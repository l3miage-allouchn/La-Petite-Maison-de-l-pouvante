-- Catalog schema. Owned by Flyway (hibernate ddl-auto=validate).

CREATE TABLE product (
    id                 VARCHAR(64)    PRIMARY KEY,
    name               VARCHAR(200)   NOT NULL,
    category           VARCHAR(32)    NOT NULL
        CHECK (category IN ('FIGURINE', 'BLURAY', 'BD', 'BOARD_GAME', 'GOODIES', 'FANZINE')),
    universe           VARCHAR(64)    NOT NULL,
    price              NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    description        TEXT,
    exclusive_evil_ed  BOOLEAN        NOT NULL DEFAULT FALSE,
    image_url          VARCHAR(500),
    CONSTRAINT product_id_slug CHECK (id ~ '^[a-z0-9][a-z0-9-]{0,63}$')
);

CREATE TABLE product_stock (
    product_id  VARCHAR(64) NOT NULL REFERENCES product (id) ON DELETE CASCADE,
    store       VARCHAR(32) NOT NULL
        CHECK (store IN ('ANGOULEME', 'AIX', 'LYON', 'LONDRES', 'ONLINE')),
    quantity    INTEGER     NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (product_id, store)
);

CREATE INDEX idx_product_category ON product (category);
CREATE INDEX idx_product_universe ON product (universe);
CREATE INDEX idx_product_stock_store ON product_stock (store) WHERE quantity > 0;
