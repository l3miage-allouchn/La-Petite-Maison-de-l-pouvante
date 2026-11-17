"""product-viewed event contract — mirrors docs/events/product-viewed.schema.json."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

PRODUCT_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"
SESSION_ID_PATTERN = r"^[A-Za-z0-9-]{8,64}$"
USER_ID_PATTERN = r"^[A-Za-z0-9-]{1,64}$"

Category = Literal["FIGURINE", "BLURAY", "BD", "BOARD_GAME", "GOODIES", "FANZINE"]
ProductId = Annotated[str, StringConstraints(pattern=PRODUCT_ID_PATTERN)]


class ProductViewedEvent(BaseModel):
    """Validated event. Unknown fields are rejected: a malformed message goes to the DLQ."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID
    event_type: Literal["product.viewed"]
    occurred_at: AwareDatetime
    user_id: Annotated[str, StringConstraints(pattern=USER_ID_PATTERN)] | None
    session_id: Annotated[str, StringConstraints(pattern=SESSION_ID_PATTERN)]
    product_id: ProductId
    category: Category
    universe: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    source: Literal["product_page"]

    @property
    def viewer_key(self) -> str:
        """Profile key: per user when authenticated, per browser session otherwise."""
        return f"u:{self.user_id}" if self.user_id else f"s:{self.session_id}"

    @property
    def timestamp(self) -> float:
        return self.occurred_at.timestamp()


def user_key(user_id: str) -> str:
    return f"u:{user_id}"
