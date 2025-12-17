from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, ProductPrice, TestPrice
from seed_data import product_prices_seed, test_prices_seed

DATABASE_URL = "sqlite:///./rfp_platform.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    for data in product_prices_seed:
        if not db.query(ProductPrice).filter_by(sku_id=data["sku_id"]).first():
            db.add(ProductPrice(**data))
            
    for data in test_prices_seed:
        if not db.query(TestPrice).filter_by(test_code=data["test_code"]).first():
            db.add(TestPrice(**data))
            
    db.commit()
    print("Database seeded!")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()