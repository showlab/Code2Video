import json
import requests
import re
from pathlib import Path
from typing import Dict, List, Optional

from prompts import get_prompt_download_assets, get_prompt_place_assets


class SmartSVGDownloader:
    def __init__(self, assets_dir: str, api_function=None, iconfinder_api_key: str = None):
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(exist_ok=True)
        self.api_function = api_function
        self.iconfinder_api_key = iconfinder_api_key

    def process_storyboard(self, storyboard: Dict) -> Dict:
        storyboard_data = json.loads(json.dumps(storyboard))
        sections = storyboard_data.get("sections", [])
        selected_sections = []
        if sections:
            selected_sections.append(sections[0])
            if len(sections) > 1:
                selected_sections.append(sections[-1])
        temp_storyboard = {"sections": selected_sections}
        # print(temp_storyboard)

        elements = self._analyze_assets_needed(temp_storyboard)

        # First, check the local cache. Only download what is missing
        downloaded_assets = {}
        for el in elements:
            cached = self._check_cache(el)
            if cached:
                downloaded_assets[el] = cached
            else:
                filepath = self._download_element(el)
                if filepath:
                    downloaded_assets[el] = filepath
                    print(f"✓ 下载: {el} -> {filepath}")

        prompt = self._build_enhancement_prompt(storyboard, downloaded_assets)
        api_response = self.api_function(prompt, max_tokens=2000)[0]

        enhanced_storyboard = self._parse_api_response(api_response, storyboard_data)
        return enhanced_storyboard

    def _build_enhancement_prompt(self, storyboard: Dict, downloaded_assets: Dict) -> str:
        asset_mapping = ""
        if downloaded_assets:
            asset_mapping = "Available Assets:\n"
            for element, filepath in downloaded_assets.items():
                asset_mapping += f"- {element}: [Asset: {filepath}]\n"
            asset_mapping += "\n"
        sections = storyboard.get("sections", [])
        animations_data = []
        if sections:
            first = sections[0]
            animations_data.append(
                {"section_index": 0, "section_id": first.get("id", ""), "animations": first.get("animations", [])}
            )
            if len(sections) > 1:
                last = sections[-1]
                animations_data.append(
                    {
                        "section_index": len(sections) - 1,
                        "section_id": last.get("id", ""),
                        "animations": last.get("animations", []),
                    }
                )
        animations_structure = json.dumps(animations_data, indent=2, ensure_ascii=False)
        return get_prompt_place_assets(asset_mapping, animations_structure)

    def _extract_json_from_markdown(self, text: str) -> str:
        pattern = r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1) if m else text

    def _parse_api_response(self, response: str, original_storyboard: Dict) -> Dict:
        """Parse API response and update storyboard"""
        try:
            try:
                content = response.candidates[0].content.parts[0].text
            except Exception:
                try:
                    content = response.choices[0].message.content
                except Exception:
                    content = str(response)

            enhanced_animations = json.loads(self._extract_json_from_markdown(content))

            # Create a copy of the storyboard for enhancement
            enhanced_storyboard = json.loads(json.dumps(original_storyboard))

            if isinstance(enhanced_animations, list):
                for anim_data in enhanced_animations:
                    section_index = anim_data.get("section_index")
                    enhanced_anims = anim_data.get("animations", [])

                    if isinstance(section_index, int) and 0 <= section_index < len(enhanced_storyboard.get("sections", [])):
                        enhanced_storyboard["sections"][section_index]["animations"] = enhanced_anims

            return enhanced_storyboard

        except json.JSONDecodeError as e:
            print(f"API response parsing failed: {e}")
            return original_storyboard
        except Exception as e:
            print(f"Error occurred while processing API response: {e}")
            return original_storyboard

    def _analyze_assets_needed(self, storyboard_data) -> List[str]:
        if not storyboard_data:
            return []

        prompt = get_prompt_download_assets(storyboard_data=storyboard_data)
        try:
            response = self.api_function(prompt, max_tokens=100)[0]
            try:
                content = response.candidates[0].content.parts[0].text
            except Exception:
                content = response.choices[0].message.content
            elements = [line.strip().lower() for line in content.strip().split("\n") if line.strip()]
            return list(dict.fromkeys(elements))[:4]
        except Exception:
            return []

    def _check_cache(self, element: str) -> Optional[str]:
        for suffix in [".png", ".svg"]:
            filepath = self.assets_dir / f"{element}{suffix}"
            if filepath.exists():
                return str(filepath.absolute())
        return None

    def _download_element(self, element: str) -> Optional[str]:
        return self._download_iconfinder(element) or self._download_iconify(element)

    def _download_iconfinder(self, element: str) -> Optional[str]:
        try:
            url = f"https://api.iconfinder.com/v4/icons/search?query={element}&count=1&premium=0"
            headers = {"Authorization": f"Bearer {self.iconfinder_api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data.get("icons"):
                return None
            raster_sizes = data["icons"][0].get("raster_sizes", [])
            size_url = None
            for size in [256, 128, 512]:
                for s in raster_sizes:
                    if s["size"] == size:
                        size_url = s["formats"][0]["preview_url"]
                        break
                if size_url:
                    break
            if not size_url and raster_sizes:
                size_url = raster_sizes[-1]["formats"][0]["preview_url"]
            if size_url:
                img_resp = requests.get(size_url, timeout=10)
                if img_resp.status_code == 200:
                    filepath = self.assets_dir / f"{element}.png"
                    filepath.write_bytes(img_resp.content)
                    return str(filepath.absolute())
        except Exception:
            return None

    def _download_iconify(self, element: str) -> Optional[str]:
        try:
            search_url = f"https://api.iconify.design/search?query={element}&limit=1"
            r = requests.get(search_url, timeout=8)
            if r.status_code == 200 and r.json().get("icons"):
                icon_id = r.json()["icons"][0]
                collection, name = icon_id.split(":", 1)
                svg_url = f"https://api.iconify.design/{collection}/{name}.svg"
                svg_resp = requests.get(svg_url, timeout=8)
                if svg_resp.status_code == 200:
                    filepath = self.assets_dir / f"{element}.svg"
                    filepath.write_text(svg_resp.text, encoding="utf-8")
                    return str(filepath.absolute())
        except Exception:
            return None

    def _enhance_animations(self, animations: List[str], assets: Dict[str, str]) -> List[str]:
        new_animations = []
        for anim in animations:
            for el, path in assets.items():
                if el in anim.lower() and path not in anim:
                    anim += f" [Asset: {path}]"
            new_animations.append(anim)
        return new_animations


def process_storyboard_with_assets(
    storyboard: Dict, api_function, assets_dir: str = "./assets/icon", iconfinder_api_key: str = None
) -> Dict:
    downloader = SmartSVGDownloader(assets_dir, api_function, iconfinder_api_key)
    return downloader.process_storyboard(storyboard)


if __name__ == "__main__":
    from gpt_request import request_gpt41_token

    sb = {
        "sections": [
            {
                "lecture_lines": ["A robot will guide the lesson", "The computer will process the data"],
                "animations": ["Show robot", "Display computer screen"],
            },
            {
                "lecture_lines": ["We will draw circles"],
                "animations": ["Draw blue circles"],
            },
        ]
    }

    downloader = SmartSVGDownloader("./assets/icon", request_gpt41_token, "Your API token")
    result = downloader.process_storyboard(sb)
    print(json.dumps(result, indent=2, ensure_ascii=False))
