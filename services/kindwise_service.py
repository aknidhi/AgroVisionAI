"""Live image identification services for AgroVision AI Crop Health Lab.

API credentials are read from the local .env file and are never stored in source code.
"""
import base64
import os
from io import BytesIO
from typing import Any

from PIL import Image
import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 45


class CropHealthAPIError(Exception):
    """Raised when an identification provider cannot return a valid result."""


def _key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise CropHealthAPIError(
            f"Missing {name}. Add it to your project's .env file and restart Streamlit."
        )
    return value


def _response_json(response: requests.Response) -> dict:
    if response.status_code == 401:
        raise CropHealthAPIError("The API key was rejected. Check the relevant key in .env.")
    if response.status_code in (402, 403):
        raise CropHealthAPIError(
            "The provider rejected this request. Your credits/quota may be exhausted, "
            "or the key may not have access to this product."
        )
    if response.status_code == 429:
        raise CropHealthAPIError("The provider rate limit was reached. Please try again later.")
    if not response.ok:
        detail = ""
        try:
            detail = response.text[:500]
        except Exception:
            pass
        raise CropHealthAPIError(
            f"Provider returned HTTP {response.status_code}. {detail}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise CropHealthAPIError("The provider returned an unreadable response.") from exc


def _image_b64(image_bytes: bytes) -> str:
    if not image_bytes:
        raise CropHealthAPIError("Please upload a valid image.")
    return base64.b64encode(image_bytes).decode("ascii")


def _kindwise_post(url: str, api_key_name: str, image_bytes: bytes,
                   params: dict | None = None) -> dict:
    response = requests.post(
        url,
        params=params or {},
        headers={"Api-Key": _key(api_key_name), "Content-Type": "application/json"},
        json={"images": [_image_b64(image_bytes)]},
        timeout=TIMEOUT,
    )
    return _response_json(response)


def _suggestions(data: dict, *paths: str) -> list[dict]:
    current: Any = data
    for path in paths:
        if not isinstance(current, dict):
            return []
        current = current.get(path)
    return current if isinstance(current, list) else []


def identify_plant_kindwise(image_bytes: bytes) -> dict:
    data = _kindwise_post(
        "https://api.plant.id/v3/identification",
        "KINDWISE_PLANT_API_KEY",
        image_bytes,
        params={"details": "common_names,url,description,taxonomy", "health": "auto"},
    )
    return {
        "provider": "Kindwise Plant.id",
        "raw": data,
        "suggestions": _suggestions(data, "result", "classification", "suggestions"),
        "health": _suggestions(data, "result", "health_assessment", "diseases"),
    }


def identify_insect_kindwise(image_bytes: bytes) -> dict:
    data = _kindwise_post(
        "https://insect.kindwise.com/api/v1/identification",
        "KINDWISE_INSECT_API_KEY",
        image_bytes,
        params={"details": "common_names,description,taxonomy,url"},
    )
    return {
        "provider": "Kindwise Insect.id",
        "raw": data,
        "suggestions": _suggestions(data, "result", "classification", "suggestions"),
    }


def identify_crop_kindwise(image_bytes: bytes) -> dict:
    data = _kindwise_post(
        "https://crop.kindwise.com/api/v1/identification",
        "KINDWISE_CROP_API_KEY",
        image_bytes,
        params={"details": "common_names,description,treatment,symptoms,severity,spreading,taxonomy,wiki_url"},
    )
    result = data.get("result", {}) if isinstance(data, dict) else {}
    crop = result.get("crop", {}).get("suggestions", [])
    disease = result.get("disease", {}).get("suggestions", [])
    return {
        "provider": "Kindwise Crop.health",
        "raw": data,
        "crop_suggestions": crop if isinstance(crop, list) else [],
        "suggestions": disease if isinstance(disease, list) else [],
    }


def _as_jpeg_upload(image_bytes: bytes, filename: str) -> tuple[str, bytes, str]:
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        return (filename.rsplit(".", 1)[0] + ".jpg", buffer.getvalue(), "image/jpeg")
    except Exception as exc:
        raise CropHealthAPIError("The uploaded image could not be prepared for Pl@ntNet.") from exc


def identify_plant_plantnet(image_bytes: bytes, filename: str = "plant.jpg") -> dict:
    key = _key("PLANTNET_API_KEY")
    upload = _as_jpeg_upload(image_bytes, filename)
    response = requests.post(
        "https://my-api.plantnet.org/v2/identify/all",
        params={"api-key": key, "lang": "en", "nb-results": 5},
        files={"images": upload},
        data={"organs": "auto"},
        timeout=TIMEOUT,
    )
    data = _response_json(response)
    suggestions = []
    for item in data.get("results", []):
        species = item.get("species", {})
        suggestions.append({
            "name": species.get("scientificNameWithoutAuthor")
                    or species.get("scientificName") or "Unknown species",
            "probability": item.get("score", 0),
            "details": {
                "common_names": species.get("commonNames", []),
                "family": species.get("family", {}).get("scientificName", ""),
            },
        })
    return {
        "provider": "Pl@ntNet (backup)",
        "raw": data,
        "suggestions": suggestions,
        "health": [],
    }


def identify_disease_plantnet(image_bytes: bytes, filename: str = "crop.jpg") -> dict:
    key = _key("PLANTNET_API_KEY")
    upload = _as_jpeg_upload(image_bytes, filename)
    response = requests.post(
        "https://my-api.plantnet.org/v2/diseases/identify",
        params={"api-key": key, "lang": "en", "nb-results": 5},
        files={"image": upload},
        data={"organs": "auto"},
        timeout=TIMEOUT,
    )
    data = _response_json(response)
    suggestions = [{
        "name": item.get("description") or item.get("name") or "Unlabelled condition",
        "probability": item.get("score", 0),
        "details": {"eppo_code": item.get("name", "")},
    } for item in data.get("results", [])]
    return {"provider": "Pl@ntNet disease beta (backup)", "raw": data,
            "suggestions": suggestions}


def identify_image(mode: str, image_bytes: bytes, filename: str = "image.jpg") -> dict:
    """Use Kindwise first; use Pl@ntNet only as a fallback where supported."""
    if mode == "Plant identification":
        try:
            return identify_plant_kindwise(image_bytes)
        except (CropHealthAPIError, requests.RequestException) as primary_error:
            try:
                result = identify_plant_plantnet(image_bytes, filename)
                result["fallback_reason"] = str(primary_error)
                return result
            except (CropHealthAPIError, requests.RequestException) as backup_error:
                raise CropHealthAPIError(
                    f"Kindwise Plant.id failed: {primary_error}\n"
                    f"Pl@ntNet fallback also failed: {backup_error}"
                ) from backup_error

    if mode == "Insect identification":
        return identify_insect_kindwise(image_bytes)

    if mode == "Crop disease analysis":
        try:
            return identify_crop_kindwise(image_bytes)
        except (CropHealthAPIError, requests.RequestException) as primary_error:
            try:
                result = identify_disease_plantnet(image_bytes, filename)
                result["fallback_reason"] = str(primary_error)
                result["coverage_note"] = (
                    "Pl@ntNet disease identification is beta and supports only a limited "
                    "list of plant species and pathologies."
                )
                return result
            except (CropHealthAPIError, requests.RequestException) as backup_error:
                raise CropHealthAPIError(
                    f"Kindwise Crop.health failed: {primary_error}\n"
                    f"Pl@ntNet disease fallback also failed: {backup_error}"
                ) from backup_error

    raise CropHealthAPIError("Select a valid analysis type.")


def get_provider_status() -> dict:
    names = {
        "Kindwise Plant.id": "KINDWISE_PLANT_API_KEY",
        "Kindwise Insect.id": "KINDWISE_INSECT_API_KEY",
        "Kindwise Crop.health": "KINDWISE_CROP_API_KEY",
        "Pl@ntNet": "PLANTNET_API_KEY",
    }
    return {label: bool(os.getenv(env_name, "").strip())
            for label, env_name in names.items()}
