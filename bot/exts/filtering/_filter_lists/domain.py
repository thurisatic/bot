from __future__ import annotations

import re
import typing
from functools import reduce
from operator import or_
from typing import Optional, Type

from bot.exts.filtering._filter_context import Event, FilterContext
from bot.exts.filtering._filter_lists.filter_list import FilterList, ListType
from bot.exts.filtering._filters.domain import DomainFilter
from bot.exts.filtering._filters.filter import Filter
from bot.exts.filtering._settings import ActionSettings
from bot.exts.filtering._utils import clean_input

if typing.TYPE_CHECKING:
    from bot.exts.filtering.filtering import Filtering

URL_RE = re.compile(r"https?://(\S+)", flags=re.IGNORECASE)


class DomainsList(FilterList):
    """
    A list of filters, each looking for a specific domain given by URL.

    The blacklist defaults dictate what happens by default when a filter is matched, and can be overridden by
    individual filters.

    Domains are found by looking for a URL schema (http or https).
    Filters will also trigger for subdomains unless set otherwise.
    """

    name = "domain"

    def __init__(self, filtering_cog: Filtering):
        super().__init__(DomainFilter)
        filtering_cog.subscribe(self, Event.MESSAGE, Event.MESSAGE_EDIT)

    def get_filter_type(self, content: str) -> Type[Filter]:
        """Get a subclass of filter matching the filter list and the filter's content."""
        return DomainFilter

    @property
    def filter_types(self) -> set[Type[Filter]]:
        """Return the types of filters used by this list."""
        return {DomainFilter}

    async def actions_for(self, ctx: FilterContext) -> tuple[Optional[ActionSettings], Optional[str]]:
        """Dispatch the given event to the list's filters, and return actions to take and a message to relay to mods."""
        text = ctx.content
        if not text:
            return None, ""

        text = clean_input(text)
        urls = {match.group(1).lower().rstrip("/") for match in URL_RE.finditer(text)}
        new_ctx = ctx.replace(content=urls)

        triggers = self.filter_list_result(
            new_ctx, self.filter_lists[ListType.DENY], self.defaults[ListType.DENY]["validations"]
        )
        ctx.notification_domain = new_ctx.notification_domain
        actions = None
        message = ""
        if triggers:
            action_defaults = self.defaults[ListType.DENY]["actions"]
            actions = reduce(
                or_,
                (filter_.actions.fallback_to(action_defaults) if filter_.actions else action_defaults
                 for filter_ in triggers
                 )
            )
            if len(triggers) == 1:
                message = f"#{triggers[0].id} (`{triggers[0].content}`)"
                if triggers[0].description:
                    message += f" - {triggers[0].description}"
            else:
                message = ", ".join(f"#{filter_.id} (`{filter_.content}`)" for filter_ in triggers)
        return actions, message
