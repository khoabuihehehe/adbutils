import os
import cv2
import numpy as np
import base64
import time
from lxml import html
from uiautomator2 import connect

current_dir = os.getcwd()

class ADB:
    def __init__(self, serial: str = None) -> None:
        """Initialize ADB connection to the device."""
        self.device = connect(serial)

    def info(self):
        """Print device information."""
        print(self.device.info)

    def shell(self, command: str):
        """Execute shell command on the device."""
        return self.device.shell(command)

    def open_link(self, url: str, package_name: str = None):
        """Open a URL in the specified package or the default browser."""
        command = f"am start -a android.intent.action.VIEW -d {url}"
        if package_name:
            command += f" {package_name}"
        self.shell(command)

    def open_app(self, package_name: str):
        """Launch the specified app using its package name."""
        self.device.app_start(package_name)

    def delete_cache(self, package_name: str):
        """Clear the cache of the specified app."""
        self.device.app_clear(package_name)

    def grant_permissions(self, package_name: str):
        """Grant necessary permissions to the specified app."""
        permissions = [
            "android.permission.WRITE_EXTERNAL_STORAGE", "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.READ_PHONE_STATE", "android.permission.CALL_PHONE",
            "android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION",
            "android.permission.CAMERA", "android.permission.READ_CONTACTS", 
            "android.permission.WRITE_CONTACTS", "android.permission.READ_CALENDAR", 
            "android.permission.WRITE_CALENDAR", "android.permission.RECORD_AUDIO"
        ]
        for permission in permissions:
            self.shell(f"pm grant {package_name} {permission}")

    def list_apps(self):
        """Print the list of installed apps on the device."""
        for app in self.device.app_list():
            print(f"{app}\r")

    def screen_capture(self) -> str:
        """Take a screenshot and save it to the resources directory."""
        os.makedirs("resources", exist_ok=True)
        path = os.path.join(current_dir, "resources", "screenshot_window_0.png")
        self.device.screenshot(path)
        return path

    def get_coordinates_image(self, target_image_path: str, threshold: float = 1) -> tuple:
        """Get the coordinates of the target image on the screen."""
        target_image = cv2.imread(target_image_path)
        template_image = cv2.imread(self.screen_capture())
        
        # Perform template matching
        result = cv2.matchTemplate(template_image, target_image, method=cv2.TM_CCOEFF_NORMED)
        y_coords, x_coords = np.where(result >= threshold)
        
        # Return the center of the first match found
        if x_coords.size > 0 and y_coords.size > 0:
            return int(x_coords[0] + target_image.shape[1] // 2), int(y_coords[0] + target_image.shape[0] // 2)
        return False

    def click(self, x: int, y: int):
        """Simulate a tap on the device at the specified coordinates."""
        self.shell(f"input tap {x} {y}")

    def click_coordinates_image(self, image_path: str):
        """Click on the coordinates of the specified image."""
        coords = self.get_coordinates_image(image_path)
        if coords:
            self.click(*coords)
        else:
            return False

    def click_text(self, text: str):
        """Click on a UI element containing the specified text."""
        self.device(text=text).click()

    def click_xpath(self, xpath: str):
        """Click on a UI element specified by its XPath."""
        if self.device.xpath(xpath=xpath).exists:
            self.device.xpath(xpath=xpath).click()
        else:
            pass

    def click_resource(self, resource_id: str):
        """Click on a UI element identified by its resource ID."""
        try:
            self.device(resourceId=resource_id).click()
        except Exception as e:
            print(f"Error clicking resource: {e}")

    def click_resource_text(self, resource_id: str, text: str):
        """Click on a UI element identified by its resource ID and text ID."""
        try:
            self.device(resourceId=resource_id, text=text).click()
        except Exception as e:
            print(f"Error clicking resource: {e}")

    def dump_xml(self) -> str:
        """Dump the current UI hierarchy as XML and save it to a file."""
        os.makedirs("resources", exist_ok=True)
        xml_file_path = os.path.join(current_dir, "resources", "window_dump_0.xml")
        xml_content = self.device.dump_hierarchy(compressed=False, pretty=False, max_depth=None)
        with open(xml_file_path, "w", encoding="utf-8") as file:
            file.write(xml_content)
        return xml_file_path

    def find_xml(self, element: str, path_file: str, index: int = 0):
        """Find coordinates of a specified element."""
        coords = []
        try:
            etree_xml = html.parse(path_file).xpath(element)
        except:
            return ([], None)
        coordinates_xml = [
            bounds.attrib["bounds"].split("][")[0].replace("[", "").split(",") 
            for bounds in etree_xml
        ]
        coords.extend(tuple(map(int, coord)) for coord in coordinates_xml)
        return (coords, etree_xml[index] if etree_xml else None)

    def get_coordinates_xml(self, element: str) -> list:
        """Get coordinates of a specified element from the dumped XML."""
        coords = []
        windows_xml_path = self.dump_xml()
        etree_xml = html.parse(windows_xml_path)
        coordinates_xml = [
            bounds.attrib["bounds"].split("][")[0].replace("[", "").split(",") 
            for bounds in etree_xml.xpath(element)
        ]
        coords.extend(tuple(map(int, coord)) for coord in coordinates_xml)
        return coords

    def check_text(self, text: str, retries: int = 30) -> bool:
        """Check if a specified text exists in the UI."""
        for _ in range(retries):
            if self.device(text=text).exists:
                return True
            time.sleep(0.5)
        return False

    def check_text_xml(self, text: str, retries: int = 30) -> bool:
        """Check if a specified text exists in the dumped XML."""
        for _ in range(retries):
            windows_xml_path = self.dump_xml()
            with open(windows_xml_path, "r", encoding="utf-8") as file:
                xml_content = file.read()
                if text in xml_content:
                    return True
            time.sleep(0.5)
        return False

    def click_coordinates_xml(self, element: str, index: int = 0):
        """Click on the coordinates of an element specified by its XPath from the XML."""
        for _ in range(15):
            part = self.get_coordinates_xml(element)
            if part:
                coords = part[index]
                self.click(coords[0], coords[1])
                return True
            time.sleep(0.5)
        return False

    def scrollable(self, element: str, times: int = 1, index: int = 0):
        """Scroll to a specified element and click on it."""
        for _ in range(15):
            part = self.get_coordinates_xml(element)
            if part:
                coords = part[index]
                for _ in range(times):
                    self.click(coords[0], coords[1])
                return True
            time.sleep(0.5)
        return False

    def send_text(self, text: str, use_vn_keyboard: bool = True, slow_typing: bool = True):
        """Send text input to the device."""
        if use_vn_keyboard:
            self.shell("ime set com.android.adbkeyboard/.AdbIME")
            time.sleep(1)
            if slow_typing:
                for char in text:
                    char_b64 = base64.b64encode(char.encode("utf-8")).decode("utf-8")
                    self.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {char_b64}")
            else:
                text_b64 = base64.b64encode(text.encode("utf-8")).decode("utf-8")
                self.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {text_b64}")
        else:
            self.shell("ime set com.android.inputmethod.pinyin/.InputService")
            time.sleep(1)
            if slow_typing:
                for char in text:
                    self.shell(f"input text '{char}'")
            else:
                self.shell(f"input text '{text}'")

    def Back(self):
        self.device.press("back")

class NodeChecker:
    def __init__(self, adb_instance: ADB) -> None:
        self.adb_instance = adb_instance

    def is_element_checked(self, **kwargs):
        max_attempts = kwargs.get("repeat", 20)
        index = kwargs.get("index", 0)

        for _ in range(max_attempts):
            xml_content = self.adb_instance.dump_xml()
            for element_name, expected_value in kwargs.items():
                is_checked, _ = self.adb_instance.find_xml(expected_value, xml_content, index=index)
                if is_checked:
                    return element_name
            time.sleep(0.5)
        return "notElement"

    def check_xml_element(self, **kwargs):
        element_name = kwargs.get("element", "")
        max_attempts = kwargs.get("repeat", 20)
        index = kwargs.get("index", 0)
        should_click = kwargs.get("click", True)

        for _ in range(max_attempts):
            coordinates = self.adb_instance.get_coordinates_xml(element_name)
            
            if coordinates:
                if index < len(coordinates):
                    x, y = coordinates[index]
                    if should_click:
                        self.adb_instance.click(x, y)
                    return True
            time.sleep(0.5)
        return False
