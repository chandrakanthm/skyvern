from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from enum import StrEnum

import structlog
from playwright.async_api import Frame, FrameLocator, Locator, Page

from skyvern.constants import SKYVERN_ID_ATTR
from skyvern.exceptions import (
    ElementIsNotComboboxDropdown,
    ElementIsNotLabel,
    ElementIsNotSelect2Dropdown,
    FailedToGetCurrentValueOfDropdown,
    MissingElement,
    MissingElementDict,
    MissingElementInCSSMap,
    MissingElementInIframe,
    MultipleDropdownAnchorErr,
    MultipleElementsFound,
    NoDropdownAnchorErr,
    NoneFrameError,
    SkyvernException,
)
from skyvern.forge.sdk.settings_manager import SettingsManager
from skyvern.webeye.scraper.scraper import ScrapedPage, get_combobox_options, get_select2_options

LOG = structlog.get_logger()

TEXT_INPUT_DELAY = 10  # 10ms between each character input
TEXT_PRESS_MAX_LENGTH = 10


async def resolve_locator(
    scrape_page: ScrapedPage, page: Page, frame: str, css: str
) -> typing.Tuple[Locator, Page | Frame]:
    iframe_path: list[str] = []

    while frame != "main.frame":
        iframe_path.append(frame)

        frame_element = scrape_page.id_to_element_dict.get(frame)
        if frame_element is None:
            raise MissingElement(element_id=frame)

        parent_frame = frame_element.get("frame")
        if not parent_frame:
            raise SkyvernException(f"element without frame: {frame_element}")

        LOG.info(f"{frame} is a child frame of {parent_frame}")
        frame = parent_frame

    current_page: Page | FrameLocator = page
    current_frame: Page | Frame = page

    while len(iframe_path) > 0:
        child_frame = iframe_path.pop()

        frame_handler = await current_frame.query_selector(f"[{SKYVERN_ID_ATTR}='{child_frame}']")
        content_frame = await frame_handler.content_frame()
        if content_frame is None:
            raise NoneFrameError(frame_id=child_frame)
        current_frame = content_frame

        current_page = current_page.frame_locator(f"[{SKYVERN_ID_ATTR}='{child_frame}']")

    return current_page.locator(css), current_frame


class InteractiveElement(StrEnum):
    A = "a"
    INPUT = "input"
    SELECT = "select"
    BUTTON = "button"


SELECTABLE_ELEMENT = [InteractiveElement.INPUT, InteractiveElement.SELECT]


class SkyvernOptionType(typing.TypedDict):
    optionIndex: int
    text: str


class SkyvernElement:
    """
    SkyvernElement is a python interface to interact with js elements built during the scarping.
    When you try to interact with these elements by python, you are supposed to use this class as an interface.
    """

    def __init__(self, locator: Locator, frame: Page | Frame, static_element: dict) -> None:
        self.__static_element = static_element
        self.__frame = frame
        self.locator = locator

    async def is_select2_dropdown(self) -> bool:
        tag_name = self.get_tag_name()
        element_class = await self.get_attr("class")
        if element_class is None:
            return False
        return (
            (tag_name == "a" and "select2-choice" in element_class)
            or (tag_name == "span" and "select2-chosen" in element_class)
            or (tag_name == "span" and "select2-arrow" in element_class)
            or (tag_name == "input" and "select2-input" in element_class)
        )

    async def is_combobox_dropdown(self) -> bool:
        tag_name = self.get_tag_name()
        role = await self.get_attr("role")
        haspopup = await self.get_attr("aria-haspopup")
        return tag_name == InteractiveElement.INPUT and role == "combobox" and haspopup == "listbox"

    async def is_checkbox(self) -> bool:
        tag_name = self.get_tag_name()
        if tag_name != "input":
            return False

        button_type = await self.get_attr("type")
        return button_type == "checkbox"

    async def is_radio(self) -> bool:
        tag_name = self.get_tag_name()
        if tag_name != "input":
            return False

        button_type = await self.get_attr("type")
        return button_type == "radio"

    def is_interactable(self) -> bool:
        return self.__static_element.get("interactable", False)

    async def is_selectable(self) -> bool:
        return (
            await self.is_select2_dropdown()
            or await self.is_combobox_dropdown()
            or self.get_tag_name() in SELECTABLE_ELEMENT
        )

    def get_tag_name(self) -> str:
        return self.__static_element.get("tagName", "")

    def get_id(self) -> str:
        return self.__static_element.get("id", "")

    def get_attributes(self) -> typing.Dict:
        return self.__static_element.get("attributes", {})

    def get_options(self) -> typing.List[SkyvernOptionType]:
        options = self.__static_element.get("options", None)
        if options is None:
            return []

        return typing.cast(typing.List[SkyvernOptionType], options)

    def get_frame(self) -> Page | Frame:
        return self.__frame

    def get_locator(self) -> Locator:
        return self.locator

    async def get_select2_dropdown(self) -> Select2Dropdown:
        if not await self.is_select2_dropdown():
            raise ElementIsNotSelect2Dropdown(self.get_id(), self.__static_element)

        return Select2Dropdown(self.get_frame(), self)

    async def get_combobox_dropdown(self) -> ComboboxDropdown:
        if not await self.is_combobox_dropdown():
            raise ElementIsNotComboboxDropdown(self.get_id(), self.__static_element)

        return ComboboxDropdown(self.get_frame(), self)

    def find_element_id_in_label_children(self, element_type: InteractiveElement) -> str | None:
        tag_name = self.get_tag_name()
        if tag_name != "label":
            raise ElementIsNotLabel(tag_name)

        children: list[dict] = self.__static_element.get("children", [])
        for child in children:
            if not child.get("interactable"):
                continue

            if child.get("tagName") == element_type:
                return child.get("id")

        return None

    async def find_label_for(
        self, dom: DomUtil, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> SkyvernElement | None:
        if self.get_tag_name() != "label":
            return None

        for_id = await self.get_attr("for")
        if for_id == "":
            return None

        locator = self.get_frame().locator(f"[id='{for_id}']")
        # supposed to be only one element, since id is unique in the whole DOM
        if await locator.count() != 1:
            return None

        unique_id = await locator.get_attribute(SKYVERN_ID_ATTR, timeout=timeout)
        if unique_id is None:
            return None

        return await dom.get_skyvern_element_by_id(unique_id)

    async def find_selectable_child(self, dom: DomUtil) -> SkyvernElement | None:
        # BFS to find the first selectable child
        index = 0
        queue = [self]
        while index < len(queue):
            item = queue[index]
            if item.is_interactable() and await item.is_selectable():
                return item

            try:
                for_element = await item.find_label_for(dom=dom)
                if for_element is not None and await for_element.is_selectable():
                    return for_element
            except Exception:
                LOG.error(
                    "Failed to find element by label-for",
                    element=item.__static_element,
                    exc_info=True,
                )

            children: list[dict] = item.__static_element.get("children", [])
            for child in children:
                child_id = child.get("id", "")
                child_element = await dom.get_skyvern_element_by_id(child_id)
                queue.append(child_element)

            index += 1
        return None

    async def get_attr(
        self,
        attr_name: str,
        dynamic: bool = False,
        timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS,
    ) -> typing.Any:
        if not dynamic:
            if attr := self.get_attributes().get(attr_name):
                return attr

        return await self.locator.get_attribute(attr_name, timeout=timeout)

    async def input_sequentially(
        self, text: str, default_timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> None:
        length = len(text)
        if length > TEXT_PRESS_MAX_LENGTH:
            # if the text is longer than TEXT_PRESS_MAX_LENGTH characters, we will locator.fill in initial texts until the last TEXT_PRESS_MAX_LENGTH characters
            # and then type the last TEXT_PRESS_MAX_LENGTH characters with locator.press_sequentially
            await self.get_locator().fill(text[: length - TEXT_PRESS_MAX_LENGTH])
            text = text[length - TEXT_PRESS_MAX_LENGTH :]

        await self.get_locator().press_sequentially(text, delay=TEXT_INPUT_DELAY, timeout=default_timeout)

    async def input_fill(
        self, text: str, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> None:
        await self.get_locator().fill(text, timeout=timeout)

    async def input_clear(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> None:
        await self.get_locator().clear(timeout=timeout)


class DomUtil:
    """
    DomUtil is a python interface to interact with the DOM.
    The ultimate goal here is to provide a full python-js interaction.
    Some functions like wait_for_xxx should be supposed to define here.
    """

    def __init__(self, scraped_page: ScrapedPage, page: Page) -> None:
        self.scraped_page = scraped_page
        self.page = page

    async def get_skyvern_element_by_id(self, element_id: str) -> SkyvernElement:
        element = self.scraped_page.id_to_element_dict.get(element_id)
        if not element:
            raise MissingElementDict(element_id)

        frame = self.scraped_page.id_to_frame_dict.get(element_id)
        if not frame:
            raise MissingElementInIframe(element_id)

        css = self.scraped_page.id_to_css_dict.get(element_id)
        if not css:
            raise MissingElementInCSSMap(element_id)

        locator, frame_content = await resolve_locator(self.scraped_page, self.page, frame, css)

        num_elements = await locator.count()
        if num_elements < 1:
            LOG.warning("No elements found with css. Validation failed.", css=css, element_id=element_id)
            raise MissingElement(selector=css, element_id=element_id)

        elif num_elements > 1:
            LOG.warning(
                "Multiple elements found with css. Expected 1. Validation failed.",
                num_elements=num_elements,
                selector=css,
                element_id=element_id,
            )
            raise MultipleElementsFound(num=num_elements, selector=css, element_id=element_id)

        return SkyvernElement(locator, frame_content, element)


class AbstractSelectDropdown(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def open(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> None:
        pass

    @abstractmethod
    async def close(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> None:
        pass

    @abstractmethod
    async def get_current_value(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> str:
        pass

    @abstractmethod
    async def get_options(
        self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> typing.List[SkyvernOptionType]:
        pass

    @abstractmethod
    async def select_by_index(
        self, index: int, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> None:
        pass


class Select2Dropdown(AbstractSelectDropdown):
    def __init__(self, frame: Page | Frame, skyvern_element: SkyvernElement) -> None:
        self.skyvern_element = skyvern_element
        self.frame = frame

    async def __find_anchor(self, timeout: float) -> Locator:
        locator = self.frame.locator("[id='select2-drop']")
        await locator.wait_for(state="visible", timeout=timeout)
        cnt = await locator.count()
        if cnt == 0:
            raise NoDropdownAnchorErr(self.name(), self.skyvern_element.get_id())
        if cnt > 1:
            raise MultipleDropdownAnchorErr(self.name(), self.skyvern_element.get_id())
        return locator

    def name(self) -> str:
        return "select2"

    async def open(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> None:
        await self.skyvern_element.get_locator().click(timeout=timeout)
        await self.__find_anchor(timeout=timeout)

    async def close(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> None:
        anchor = await self.__find_anchor(timeout=timeout)
        await anchor.press("Escape", timeout=timeout)

    async def get_current_value(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> str:
        tag_name = self.skyvern_element.get_tag_name()
        if tag_name == "input":
            # TODO: this is multiple options case, we haven't fully supported it yet.
            return ""

        # check SkyvernElement.is_select2_dropdown() method, only <a> and <span> element left
        # we should make sure the locator is on <a>, so we're able to find the [class="select2-chosen"] child
        locator = self.skyvern_element.get_locator()
        if tag_name == "span":
            locator = locator.locator("..")
        elif tag_name == "a":
            pass
        else:
            raise FailedToGetCurrentValueOfDropdown(
                self.name(), self.skyvern_element.get_id(), "invalid element of select2"
            )

        try:
            return await locator.locator("span[class='select2-chosen']").text_content(timeout=timeout)
        except Exception as e:
            raise FailedToGetCurrentValueOfDropdown(self.name(), self.skyvern_element.get_id(), repr(e))

    async def get_options(
        self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> typing.List[SkyvernOptionType]:
        anchor = await self.__find_anchor(timeout=timeout)
        element_handler = await anchor.element_handle(timeout=timeout)
        options = await get_select2_options(self.frame, element_handler)
        return typing.cast(typing.List[SkyvernOptionType], options)

    async def select_by_index(
        self, index: int, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> None:
        anchor = await self.__find_anchor(timeout=timeout)
        options = anchor.locator("li[role='option']")
        await options.nth(index).click(timeout=timeout)


class ComboboxDropdown(AbstractSelectDropdown):
    def __init__(self, frame: Page | Frame, skyvern_element: SkyvernElement) -> None:
        self.skyvern_element = skyvern_element
        self.frame = frame

    async def __find_anchor(self, timeout: float) -> Locator:
        control_id = await self.skyvern_element.get_attr("aria-controls", timeout=timeout)
        locator = self.frame.locator(f"[id='{control_id}']")
        await locator.wait_for(state="visible", timeout=timeout)
        cnt = await locator.count()
        if cnt == 0:
            raise NoDropdownAnchorErr(self.name(), self.skyvern_element.get_id())
        if cnt > 1:
            raise MultipleDropdownAnchorErr(self.name(), self.skyvern_element.get_id())
        return locator

    def name(self) -> str:
        return "combobox"

    async def open(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> None:
        await self.skyvern_element.get_locator().click(timeout=timeout)
        await self.__find_anchor(timeout=timeout)

    async def close(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> None:
        await self.skyvern_element.get_locator().press("Tab", timeout=timeout)

    async def get_current_value(self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS) -> str:
        try:
            return await self.skyvern_element.get_attr("value", dynamic=True, timeout=timeout)
        except Exception as e:
            raise FailedToGetCurrentValueOfDropdown(self.name(), self.skyvern_element.get_id(), repr(e))

    async def get_options(
        self, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> typing.List[SkyvernOptionType]:
        anchor = await self.__find_anchor(timeout=timeout)
        element_handler = await anchor.element_handle()
        options = await get_combobox_options(self.frame, element_handler)
        return typing.cast(typing.List[SkyvernOptionType], options)

    async def select_by_index(
        self, index: int, timeout: float = SettingsManager.get_settings().BROWSER_ACTION_TIMEOUT_MS
    ) -> None:
        anchor = await self.__find_anchor(timeout=timeout)
        options = anchor.locator("li[role='option']")
        await options.nth(index).click(timeout=timeout)
