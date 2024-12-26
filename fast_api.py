import asyncio
import json
from fastapi import FastAPI, Depends, HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect
import nats
from mvideo import get_data_mvideo
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

class Prices(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    price: int
    link: str

class ConnectionManager:
    def __init__(self):
        self.connections = []

    async def product_action(self, msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        print("Received a message on '{subject} {reply}': {data}".format(
            subject=subject, reply=reply, data=data))
        await self.broadcast(f"{subject}: {data}")

    async def init(self):
        self.nc = await nats.connect("nats://127.0.0.1:4222")
        await self.nc.subscribe("created_product", cb=self.product_action)
        await self.nc.subscribe("deleted_product", cb=self.product_action)
        await self.nc.subscribe("update_product", cb=self.product_action)
        await self.nc.subscribe("updated_product", cb=self.product_action)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    async def broadcast(self, data):
        for conn in self.connections:
            await conn.send_text(data)

app = FastAPI()
sqlite_url = "sqlite:///parser.db"
engine = create_engine(sqlite_url)
manager = ConnectionManager()

def get_async_session():
    sqlite_url = "sqlite+aiosqlite:///parser.db"
    engine_2 = create_async_engine(sqlite_url)
    dbsession = async_sessionmaker(engine_2)
    return dbsession()


async def get_session():
    async with get_async_session() as session:
        yield session


SessionDep = Depends(get_session)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


async def background_parser_async():
    while True:
        print("Starting get price")
        async with (get_async_session() as session):
            product_count = 0
            async for product in get_data_mvideo():
                existing_product = await session.execute(
                    select(Prices).where(Prices.id == product['id'])
                )
                existing_product = existing_product.scalar_one_or_none()
                p = Prices(**product)
                if existing_product is None:
                    session.add(p)
                    await session.commit()
                    product_count += 1
                elif existing_product.price != product['price']:
                    await update_item(product['id'], p)
                if product_count % 100 == 0 and product_count > 0:
                    await manager.broadcast(f"В базу добавлен {product_count} товар")
            await manager.broadcast(f"Всего в базе {product_count} товаров")
        await asyncio.sleep(12 * 60 * 60)


@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    asyncio.create_task(background_parser_async())
    await manager.init()


@app.get("/prices")
async def read_prices(session: Session = SessionDep, offset: int = 0, limit: int = 100):
    stmt = select(Prices).offset(offset).limit(limit)
    items = await session.scalars(stmt)
    await manager.broadcast(f"Произошло чтение {limit} товаров")
    return items.all()


@app.get("/prices/{item_id}")
async def read_item(item_id: int, session: Session = SessionDep):
    price = await session.get(Prices, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    await manager.broadcast(f"Произошло чтение товара с id = {item_id}")
    return price


@app.put("/prices/{item_id}")
async def update_item(item_id: int, data: Prices, session: Session = SessionDep):
    price_db = await session.get(Prices, item_id)
    if not price_db:
        raise HTTPException(status_code=404, detail="Price not found")
    _data = price_db.model_dump_json().encode()
    await manager.nc.publish("update_product", _data)
    price_data = data.model_dump(exclude_unset=True)
    price_db.sqlmodel_update(price_data)
    session.add(price_db)
    await session.commit()
    await session.refresh(price_db)
    _data = price_db.model_dump_json().encode()
    await manager.nc.publish("updated_product", _data)
    return price_db


@app.post("/prices/create")
async def create_item(item: Prices, session: Session = SessionDep):
    session.add(item)
    await session.commit()
    await session.refresh(item)
    data = item.model_dump_json().encode()
    await manager.nc.publish("created_product", data)
    return item


@app.delete("/prices/{item_id}")
async def delete_item(item_id: int, session: Session = SessionDep):
    price = await session.get(Prices, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    await session.delete(price)
    await session.commit()
    data = price.model_dump_json().encode()
    await manager.nc.publish("deleted_product", data)
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket : WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            async with get_async_session() as session:
                match data:
                    case "read_prices":
                        response = await read_prices(session)
                        response = json.dumps(
                            [
                                item.model_dump() for item in response
                            ])
                        await websocket.send_text(response)
                    case _:
                        await websocket.send_text("Извините такой команды нет")
    except WebSocketDisconnect:
        print("disconnect")