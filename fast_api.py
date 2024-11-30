import asyncio
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from mvideo import get_data_mvideo
from starlette.concurrency import run_in_threadpool
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

app = FastAPI()

class Prices(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    cost: int
    link: str

sqlite_url = "sqlite:///parser.db"
engine = create_engine(sqlite_url)

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
        # await asyncio.sleep(12 * 60 * 60)
        data = await run_in_threadpool(get_data_mvideo)
        session = get_async_session()
        for i in data:
            print(i)
            existing_product = await session.execute(
                select(Prices).where(Prices.link == i["link"])
            )
            if existing_product.scalar_one_or_none() is None:
                # Если продукт не найден, добавляем его
                p = Prices(**i)
                session.add(p)
                await session.commit()

        # add_item(title, price, index)
        await asyncio.sleep(12 * 60 * 60)

# def background_add_item():
#     data = get_price()
#     # add_item(*data)

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    asyncio.create_task(background_parser_async())

# @app.get("/start_parser")
# async def start_parser(background_tasks: BackgroundTasks):
#     #  asyncio.create_task(background_add_item())
#     background_tasks.add_task(background_add_item)
#     return {}

@app.get("/prices")
async def read_prices(session: Session = SessionDep, offset: int = 0, limit: int = 100):
    # return session.exec(select(Prices).offset(offset).limit(limit)).all()
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
    session.refresh(price_db)
    return price_db

@app.post("/prices/create")
async def create_item(item: Prices, session: Session = SessionDep):
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

@app.delete("/prices/{item_id}")
async def delete_item(item_id: int, session: Session = SessionDep):
    price = await session.get(Prices, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    await session.delete(price)
    await session.commit()
    return {"ok": True}