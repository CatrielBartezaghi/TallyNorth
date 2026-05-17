import sys
import os
import random
from datetime import datetime, timedelta

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.currency import Currency
from app.models.credit_card import CreditCard
from app.models.purchase import CreditCardPurchase
from app.models.installment import Installment
from app.models.budget import Budget
from app.models.saving_goal import SavingGoal
from app.models.investment import Investment
from app.services.auth import get_password_hash

def seed_demo_data():
    db = SessionLocal()
    try:
        print("Starting Demo Account Seed Process...")
        demo_email = "demo@finance.com"
        
        # 1. Clean up existing demo user
        demo_user = db.query(User).filter(User.email == demo_email).first()
        if demo_user:
            print("Found existing demo user. Wiping all associated data...")
            # We must delete in the correct order to respect foreign keys
            # Fetch objects to delete so cascade doesn't mess up if set incorrectly
            purchases = db.query(CreditCardPurchase).join(CreditCard).filter(CreditCard.user_id == demo_user.id).all()
            for p in purchases:
                db.query(Installment).filter(Installment.purchase_id == p.id).delete(synchronize_session=False)
            db.query(CreditCardPurchase).filter(CreditCardPurchase.credit_card_id.in_([c.id for c in db.query(CreditCard.id).filter(CreditCard.user_id == demo_user.id)])).delete(synchronize_session=False)
            db.query(Transaction).filter(Transaction.user_id == demo_user.id).delete(synchronize_session=False)
            db.query(CreditCard).filter(CreditCard.user_id == demo_user.id).delete(synchronize_session=False)
            db.query(Budget).filter(Budget.user_id == demo_user.id).delete(synchronize_session=False)
            db.query(SavingGoal).filter(SavingGoal.user_id == demo_user.id).delete(synchronize_session=False)
            db.query(Investment).filter(Investment.user_id == demo_user.id).delete(synchronize_session=False)
            db.query(Account).filter(Account.user_id == demo_user.id).delete(synchronize_session=False)
            db.query(Category).filter(Category.user_id == demo_user.id).delete(synchronize_session=False)
            db.commit()
            print("Wiped old data.")
        else:
            demo_user = User(
                email=demo_email,
                hashed_password=get_password_hash("demo123"),
                is_active=True
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
            print("Created new Demo user.")

        # 2. Currencies
        print("Setting up currencies...")
        def get_or_create_currency(code, name, symbol, is_crypto=False):
            curr = db.query(Currency).filter(Currency.code == code).first()
            if not curr:
                curr = Currency(code=code, name=name, symbol=symbol, decimal_places=8 if is_crypto else 2, is_crypto=is_crypto)
                db.add(curr)
                db.commit()
                db.refresh(curr)
            return curr

        usd = get_or_create_currency("USD", "US Dollar", "$")
        eur = get_or_create_currency("EUR", "Euro", "€")
        btc = get_or_create_currency("BTC", "Bitcoin", "₿", is_crypto=True)

        # 3. Categories (English)
        print("Setting up categories...")
        categories_data = [
            # Income
            {"name": "Salary", "type": "income", "color": "#10b981", "icon": "briefcase"},
            {"name": "Freelance", "type": "income", "color": "#3b82f6", "icon": "laptop"},
            {"name": "Investments", "type": "income", "color": "#8b5cf6", "icon": "trending-up"},
            # Expenses
            {"name": "Housing", "type": "expense", "color": "#ef4444", "icon": "home"},
            {"name": "Groceries", "type": "expense", "color": "#f59e0b", "icon": "shopping-cart"},
            {"name": "Dining Out", "type": "expense", "color": "#f97316", "icon": "utensils"},
            {"name": "Transportation", "type": "expense", "color": "#6366f1", "icon": "car"},
            {"name": "Entertainment", "type": "expense", "color": "#ec4899", "icon": "film"},
            {"name": "Utilities", "type": "expense", "color": "#06b6d4", "icon": "zap"},
            {"name": "Health", "type": "expense", "color": "#14b8a6", "icon": "heart"},
            {"name": "Shopping", "type": "expense", "color": "#8b5cf6", "icon": "shopping-bag"},
        ]
        
        category_map = {}
        for cdata in categories_data:
            cat = db.query(Category).filter(Category.name == cdata["name"]).first()
            if cat:
                cat.user_id = demo_user.id
                cat.type = cdata["type"]
                cat.color = cdata["color"]
                cat.icon = cdata["icon"]
                cat.is_active = True
            else:
                cat = Category(user_id=demo_user.id, **cdata, is_active=True)
                db.add(cat)
            db.commit()
            db.refresh(cat)
            category_map[cat.name] = cat

        # 4. Accounts
        print("Setting up accounts...")
        checking = Account(user_id=demo_user.id, name="Main Checking", type="checking", currency_id=usd.id, initial_balance=5500.00)
        savings = Account(user_id=demo_user.id, name="Emergency Fund", type="savings", currency_id=usd.id, initial_balance=15000.00)
        euro_wallet = Account(user_id=demo_user.id, name="Euro Wallet", type="cash", currency_id=eur.id, initial_balance=850.00)
        
        db.add_all([checking, savings, euro_wallet])
        db.commit()
        db.refresh(checking)
        db.refresh(savings)

        # 5. Credit Cards
        print("Setting up credit cards...")
        visa = CreditCard(
            user_id=demo_user.id,
            name="Visa Platinum",
            closing_day=25,
            due_day=5,
            currency_id=usd.id,
            payment_account_id=checking.id,
            credit_limit=10000.00
        )
        mc = CreditCard(
            user_id=demo_user.id,
            name="Mastercard Black",
            closing_day=20,
            due_day=1,
            currency_id=usd.id,
            payment_account_id=None,
            credit_limit=15000.00
        )
        db.add_all([visa, mc])
        db.commit()
        db.refresh(visa)

        # 6. Historical Transactions
        print("Generating historical transactions...")
        transactions = []
        today = datetime.now().date()
        
        # Salary every month
        for i in range(6):
            salary_date = today.replace(day=1) - timedelta(days=30 * i)
            transactions.append(Transaction(
                user_id=demo_user.id, account_id=checking.id, category_id=category_map["Salary"].id,
                type="income", amount=4500.00, description="TechCorp Salary",
                date=salary_date, is_recurring=False
            ))
            
            # Rent
            rent_date = today.replace(day=5) - timedelta(days=30 * i)
            transactions.append(Transaction(
                user_id=demo_user.id, account_id=checking.id, category_id=category_map["Housing"].id,
                type="expense", amount=1500.00, description="Apartment Rent",
                date=rent_date, is_recurring=False
            ))

            # Internet/Utilities
            transactions.append(Transaction(
                user_id=demo_user.id, account_id=checking.id, category_id=category_map["Utilities"].id,
                type="expense", amount=120.00, description="Internet & Phone",
                date=today.replace(day=10) - timedelta(days=30 * i), is_recurring=False
            ))

        # Random daily expenses for the last 90 days
        for i in range(90):
            current_date = today - timedelta(days=i)
            # Coffee/Snack
            if random.random() > 0.3:
                transactions.append(Transaction(
                    user_id=demo_user.id, account_id=checking.id, category_id=category_map["Dining Out"].id,
                    type="expense", amount=round(random.uniform(4.5, 15.0), 2), description="Starbucks / Cafe",
                    date=current_date, is_recurring=False
                ))
            
            # Groceries every ~5 days
            if i % 5 == 0:
                transactions.append(Transaction(
                    user_id=demo_user.id, account_id=checking.id, category_id=category_map["Groceries"].id,
                    type="expense", amount=round(random.uniform(60.0, 150.0), 2), description="Whole Foods Market",
                    date=current_date, is_recurring=False
                ))
                
            # Transport
            if random.random() > 0.5:
                transactions.append(Transaction(
                    user_id=demo_user.id, account_id=checking.id, category_id=category_map["Transportation"].id,
                    type="expense", amount=round(random.uniform(15.0, 40.0), 2), description="Uber / Gas",
                    date=current_date, is_recurring=False
                ))

        db.add_all(transactions)
        db.commit()

        # 7. Credit Card Purchases & Installments
        print("Generating credit card purchases & installments...")
        
        def create_purchase(card, cat, desc, amount, installments, months_ago):
            purchase_date = today - timedelta(days=30 * months_ago)
            purchase = CreditCardPurchase(
                user_id=demo_user.id, credit_card_id=card.id, category_id=cat.id, description=desc,
                total_amount=amount, installments=installments,
                installment_amount=round(amount / installments, 2),
                purchase_date=purchase_date, first_installment_date=purchase_date + timedelta(days=20)
            )
            db.add(purchase)
            db.commit()
            db.refresh(purchase)
            
            # Generate installments
            for i in range(installments):
                due_date = purchase.first_installment_date + timedelta(days=30 * i)
                is_paid = due_date < today
                inst = Installment(
                    user_id=demo_user.id, purchase_id=purchase.id, installment_number=i+1,
                    due_date=due_date, amount=purchase.installment_amount,
                    is_paid=is_paid, paid_account_id=checking.id if is_paid else None,
                    paid_at=due_date if is_paid else None
                )
                db.add(inst)
            db.commit()

        create_purchase(visa, category_map["Shopping"], "MacBook Pro M3", 2400.00, 6, 2)
        create_purchase(visa, category_map["Entertainment"], "Coachella Tickets", 800.00, 3, 1)
        create_purchase(mc, category_map["Transportation"], "Flights to Tokyo", 1200.00, 4, 3)

        # 8. Budgets
        print("Setting up budgets...")
        curr_month = today.replace(day=1).strftime("%Y-%m-%d")
        b1 = Budget(user_id=demo_user.id, category_id=category_map["Groceries"].id, currency_id=usd.id, period_start=curr_month, amount=600.00, notes="Try to eat out less")
        b2 = Budget(user_id=demo_user.id, category_id=category_map["Dining Out"].id, currency_id=usd.id, period_start=curr_month, amount=250.00, notes="Weekends only")
        b3 = Budget(user_id=demo_user.id, category_id=category_map["Entertainment"].id, currency_id=usd.id, period_start=curr_month, amount=150.00, notes="")
        db.add_all([b1, b2, b3])
        db.commit()

        # 9. Saving Goals
        print("Setting up saving goals...")
        g1 = SavingGoal(user_id=demo_user.id, name="New Car", currency_id=usd.id, target_amount=25000.00, current_amount=8500.00, target_date=(today + timedelta(days=365)).strftime("%Y-%m-%d"), color="#3b82f6", icon="car")
        g2 = SavingGoal(user_id=demo_user.id, name="Europe Trip", currency_id=usd.id, target_amount=5000.00, current_amount=3200.00, target_date=(today + timedelta(days=120)).strftime("%Y-%m-%d"), color="#10b981", icon="plane")
        db.add_all([g1, g2])
        db.commit()

        # 10. Investments
        print("Setting up investments...")
        inv1 = Investment(user_id=demo_user.id, name="S&P 500 ETF (VOO)", type="fund", currency_id=usd.id, invested_amount=12000.00, current_value=13450.00, expected_return_rate=8.5, notes="Vanguard ETF")
        inv2 = Investment(user_id=demo_user.id, name="Bitcoin Holdings", type="crypto", currency_id=btc.id, invested_amount=0.5, current_value=0.55, expected_return_rate=None, notes="Cold storage")
        inv3 = Investment(user_id=demo_user.id, name="Apple Stock (AAPL)", type="stock", currency_id=usd.id, invested_amount=3000.00, current_value=3250.00, expected_return_rate=12.0, notes="Tech stocks")
        db.add_all([inv1, inv2, inv3])
        db.commit()

        print("Done! Demo account is fully seeded and ready for showcase.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
