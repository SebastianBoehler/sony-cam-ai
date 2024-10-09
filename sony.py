import requests
import time
import subprocess
import json
import logging
import os
from ai_optimizer import optimize_camera_settings

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Replace with the correct camera URL (port 8080)
CAMERA_URL = "http://192.168.122.1:8080/sony/camera"


def send_request(method, params=[]):
    payload = {"method": method, "params": params, "id": 1, "version": "1.0"}
    headers = {"Content-Type": "application/json"}
    response = requests.post(CAMERA_URL, json=payload, headers=headers)
    logging.debug(f"Request for {method}: {json.dumps(payload)}")
    logging.debug(f"Response for {method}: {response.text}")
    return response


def ping_camera(ip):
    try:
        output = subprocess.run(["ping", "-c", "3", ip], capture_output=True, text=True)
        return output.returncode == 0
    except Exception as e:
        logging.error(f"Error pinging camera: {e}")
        return False


def get_available_api_methods():
    response = send_request("getAvailableApiList")
    if response.status_code == 200:
        logging.info("Available API methods retrieved successfully")
    else:
        logging.error(f"Failed to get API list: {response.status_code}")


def start_rec_mode():
    response = send_request("startRecMode")
    if response.status_code == 200:
        logging.info("Recording mode started successfully!")
    else:
        logging.error(f"Failed to start recording mode: {response.status_code}")


def wait_for_camera_ready():
    max_attempts = 10
    for attempt in range(max_attempts):
        logging.debug(f"Attempt {attempt + 1} to check if camera is ready")
        response = send_request("getEvent", [False])
        if response.status_code == 200:
            result = response.json()
            logging.debug(f"getEvent response: {json.dumps(result, indent=2)}")

            # Find the camera status in the result list
            status = None
            for item in result.get("result", []):
                if isinstance(item, dict) and item.get("type") == "cameraStatus":
                    status = item.get("cameraStatus")
                    break

            logging.debug(f"Camera status: {status}")
            if status == "IDLE":
                logging.info("Camera is ready!")
                return True
        else:
            logging.error(f"Failed to get camera status: {response.status_code}")
        time.sleep(2)
    logging.error("Camera did not become ready in time")
    return False


def get_camera_settings():
    settings = {}
    setting_methods = {
        "shutter_speed": "getShutterSpeed",
        "aperture": "getAvailableFNumber",
        "iso": "getIsoSpeedRate",
        "white_balance": "getWhiteBalance",
        "focus_mode": "getFocusMode",
        "exposure_compensation": "getExposureCompensation",
        "zoom": "getZoomSetting",
    }

    for setting, method in setting_methods.items():
        response = send_request(method)
        if response.status_code == 200:
            result = response.json().get("result", [None])[0]
            settings[setting] = result

    logging.info(f"Current camera settings: {settings}")
    return settings


def set_camera_setting(setting, value):
    setting_methods = {
        "shutter_speed": "setShutterSpeed",
        "aperture": "setFNumber",
        "iso": "setIsoSpeedRate",
        "white_balance": "setWhiteBalance",
        "focus_mode": "setFocusMode",
        "exposure_compensation": "setExposureCompensation",
        "zoom": "actZoom",
    }

    method = setting_methods.get(setting)
    if not method:
        logging.warning(f"Unknown setting: {setting}")
        return False

    if setting == "zoom":
        return set_zoom(value)
    else:
        response = send_request(method, [value])
        logging.info(f"Setting {setting} to {value}. Status: {response.status_code}")
        return response.status_code == 200


def set_zoom(value):
    if not isinstance(value, (int, float)):
        logging.warning(f"Invalid zoom value: {value}")
        return False

    target_zoom = int(value)
    current_zoom = get_available_settings()["zoom"]["current"]
    max_zoom = get_available_settings()["zoom"]["max"]

    if target_zoom < 0 or target_zoom > max_zoom:
        logging.warning(f"Zoom value {target_zoom} is out of range (0-{max_zoom})")
        return False

    if target_zoom > current_zoom:
        direction = "in"
    else:
        direction = "out"

    steps = abs(target_zoom - current_zoom)
    logging.info(f"Attempting to zoom {direction} by {steps} steps")

    for _ in range(steps):
        response = send_request("actZoom", [direction, "1shot"])
        if response.status_code != 200:
            logging.error(f"Failed to perform zoom action: {response.status_code}")
            return False
        time.sleep(0.5)  # Short delay between zoom steps

    logging.info(f"Zoom action completed. Target zoom: {target_zoom}")
    time.sleep(2)  # Wait for zoom to stabilize
    return True


def get_available_settings():
    available_settings = {}
    setting_methods = {
        "shutter_speed": "getAvailableShutterSpeed",
        "aperture": "getAvailableFNumber",
        "iso": "getAvailableIsoSpeedRate",
        "white_balance": "getAvailableWhiteBalance",
        "focus_mode": "getAvailableFocusMode",
        "exposure_compensation": "getAvailableExposureCompensation",
        "zoom": "getZoomSetting",
    }

    for setting, method in setting_methods.items():
        response = send_request(method)
        if response.status_code == 200:
            result = response.json().get("result", [])
            if setting == "white_balance":
                available_settings[setting] = [
                    wb.get("whiteBalanceMode")
                    for wb in result[1]
                    if isinstance(wb, dict)
                ]
            elif setting == "zoom":
                zoom_info = result[0]
                available_settings[setting] = {
                    "current": zoom_info.get("zoomPosition", 0),
                    "min": 0,
                    "max": zoom_info.get("zoomNumberBox", 100),
                }
            else:
                available_settings[setting] = result[1] if len(result) > 1 else result

    logging.info(f"Available settings: {json.dumps(available_settings, indent=4)}")
    return available_settings


def take_picture_and_optimize(prompt, output_dir):
    initial_settings = get_camera_settings()
    available_settings = get_available_settings()

    response = send_request("actTakePicture")
    if response.status_code != 200:
        logging.error("Failed to take initial picture")
        return False

    image_url = response.json().get("result", [[]])[0][0]
    initial_image_path = os.path.join(output_dir, "initial_image.jpg")

    image_response = requests.get(image_url)
    if image_response.status_code == 200:
        with open(initial_image_path, "wb") as f:
            f.write(image_response.content)
        logging.info(f"Initial image saved to {initial_image_path}")
    else:
        logging.error("Failed to download initial image")
        return False

    current_zoom = available_settings["zoom"]["current"]
    max_zoom = available_settings["zoom"]["max"]
    ai_prompt = (
        f"{prompt} The current zoom is at {current_zoom} and can go up to {max_zoom}. "
        f"Please provide a single zoom value between {current_zoom} and {max_zoom} to significantly increase the zoom level. "
        f"Also optimize other camera settings for the best image quality at this zoom level."
    )

    optimized_settings = optimize_camera_settings(
        initial_image_path, ai_prompt, initial_settings, available_settings
    )
    logging.info(f"Optimized settings: {optimized_settings}")

    optimized_settings_dict = json.loads(optimized_settings)

    # Apply zoom first
    if "zoom" in optimized_settings_dict:
        zoom_value = optimized_settings_dict.pop("zoom")
        if not set_zoom(zoom_value):
            logging.error("Failed to apply zoom setting")
            return False

    # Apply other settings
    for setting, value in optimized_settings_dict.items():
        set_camera_setting(setting, value)

    # Take another picture with optimized settings
    optimized_response = send_request("actTakePicture")
    if optimized_response.status_code == 200:
        optimized_image_url = optimized_response.json().get("result", [[]])[0][0]
        optimized_image_path = os.path.join(output_dir, "optimized_image.jpg")

        optimized_image_response = requests.get(optimized_image_url)
        if optimized_image_response.status_code == 200:
            with open(optimized_image_path, "wb") as f:
                f.write(optimized_image_response.content)
            logging.info(f"Optimized image saved to {optimized_image_path}")
            return True
        else:
            logging.error("Failed to download optimized image")
    else:
        logging.error("Failed to take optimized picture")

    return False


def create_output_directory():
    output_dir = "output_images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir


if __name__ == "__main__":
    camera_ip = "192.168.122.1"
    if ping_camera(camera_ip):
        logging.debug("Camera ping successful")
        get_available_api_methods()
        start_rec_mode()

        initialization_delay = 10
        logging.info(
            f"Waiting {initialization_delay} seconds for camera initialization..."
        )
        time.sleep(initialization_delay)

        if wait_for_camera_ready():
            output_dir = create_output_directory()
            prompt = "Capture a well-composed and detailed image of the scene. Zoom in significantly to focus on the most interesting part of the scene."
            if take_picture_and_optimize(prompt, output_dir):
                logging.info("Image capture and optimization completed successfully")
            else:
                logging.error("Failed to capture and optimize image")
        else:
            logging.error("Camera did not become ready. Exiting.")
    else:
        logging.error("Camera is not reachable. Exiting.")
