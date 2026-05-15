import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.currency import Currency
from app.services.auth import get_password_hash
import uuid

def seed_demo_data():
    db = SessionLocal()
    try:
        print("Buscando o creando usuario Demo...")
        demo_email = "demo@finance.com"
        demo_user = db.query(User).filter(User.email == demo_email).first()
        
        if not demo_user:
            demo_user = User(
                email=demo_email,
                hashed_password=get_password_hash("demo123"),
                is_active=True
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
            print("Usuario Demo creado con éxito.")
        else:
            print("El usuario Demo ya existe. Recreando sus datos...")
            # En un entorno real, aquí borraríamos todos los datos viejos de la Demo.
            # db.query(Transaction).filter(Transaction.user_id == demo_user.id).delete()
            # db.query(Account).filter(Account.user_id == demo_user.id).delete()
            # db.commit()

        # Check if ARS currency exists
        ars_currency = db.query(Currency).filter(Currency.code == "ARS").first()
        if not ars_currency:
            ars_currency = Currency(code="ARS", name="Peso Argentino", symbol="$", decimal_places=2, is_crypto=False)
            db.add(ars_currency)
            db.commit()
            db.refresh(ars_currency)

        # Crear cuenta si no tiene
        account = db.query(Account).filter(Account.user_id == demo_user.id, Account.name == "Banco Demo").first()
        if not account:
            account = Account(
                user_id=demo_user.id,
                name="Banco Demo",
                type="checking",
                currency_id=ars_currency.id,
                initial_balance=500000.00
            )
            db.add(account)
            db.commit()
            db.refresh(account)

        # Crear transacciones de prueba
        transactions = db.query(Transaction).filter(Transaction.user_id == demo_user.id).count()
        if transactions == 0:
            print("Creando transacciones de prueba...")
            for i in range(1, 15):
                t = Transaction(
                    user_id=demo_user.id,
                    account_id=account.id,
                    type="expense" if i % 2 == 0 else "income",
                    amount=15000.00 * i,
                    description=f"Movimiento de prueba {i}",
                    date=datetime.now().date() - timedelta(days=i),
                    is_recurring=False
                )
                db.add(t)
            db.commit()
            print("Transacciones creadas.")

        print("¡Datos Demo generados correctamente!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
