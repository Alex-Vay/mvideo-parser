import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Depends, HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect
from tensorflow.python.distribute.multi_process_runner import manager
import nats
from mvideo import get_data_mvideo
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

class Prices(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    cost: int
    link: str

class ConnectionManager:
    def __init__(self):
        self.connections = []

    async def message_handler(self, msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        print("Received a message on '{subject} {reply}': {data}".format(
            subject=subject, reply=reply, data=data))
        await self.broadcast(data)

    async def init(self):
        self.nc = await nats.connect("nats://127.0.0.1:4222")
        sub = await self.nc.subscribe("created_price", cb=self.message_handler)

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
# ns = await nats.connect("nats://127.0.0.1:4222")

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


# async def background_parser_async():
#     while True:
#         print("Starting get price")
#         async with get_async_session() as session:
#             async for product in get_data_mvideo():
#                 existing_product = await session.execute(
#                     select(Prices).where(Prices.link == product["link"])
#                 )
#                 if existing_product.scalar_one_or_none() is None:
#                     p = Prices(**product)
#                     session.add(p)
#                     await session.commit()
#         await asyncio.sleep(12 * 60 * 60)
#
#
# @app.on_event("startup")
# async def startup_event():
#     create_db_and_tables()
#     executor = ThreadPoolExecutor(max_workers=3)
#     executor.submit(run_async_task_in_thread, background_parser_async())
#
#
# def run_async_task_in_thread(coro):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(coro)


async def background_parser_async():
    while True:
        print("Starting get price")
        async with get_async_session() as session:
            async for product in get_data_mvideo():
                existing_product = await session.execute(
                    select(Prices).where(Prices.id == product['id'])
                )
                if existing_product.scalar_one_or_none() is None:
                    p = Prices(**product)
                    session.add(p)
                    await session.commit()
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
    return items.all()


@app.get("/prices/{item_id}")
async def read_item(item_id: int, session: Session = SessionDep):
    price = await session.get(Prices, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    return price


@app.put("/prices/{item_id}")
async def update_item(item_id: int, data: Prices, session: Session = SessionDep):
    price_db = await session.get(Prices, item_id)
    if not price_db:
        raise HTTPException(status_code=404, detail="Price not found")
    price_data = data.model_dump(exclude_unset=True)
    price_db.sqlmodel_update(price_data)
    session.add(price_db)
    await session.commit()
    await session.refresh(price_db)
    return price_db


@app.post("/prices/create")
async def create_item(item: Prices, session: Session = SessionDep):
    session.add(item)
    await session.commit()
    await session.refresh(item)
    data = item.model_dump_json().encode()
    await manager.nc.publish("created_price", data)
    return item


@app.delete("/prices/{item_id}")
async def delete_item(item_id: int, session: Session = SessionDep):
    price = await session.get(Prices, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    await session.delete(price)
    await session.commit()
    return {"ok": True}

@app.websocket("/ws")
async def websocket_endpoint(websocket : WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "read_prices":
                dbsession = get_async_session()
                response = await read_prices(dbsession)
                response = json.dumps(
                    [
                        item.model_dump() for item in response
                    ])
                await websocket.send_text(response)
            await websocket.send_text(data * 3)
    except WebSocketDisconnect:
        print("disconnect")