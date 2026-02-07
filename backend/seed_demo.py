"""Seed demo data for INFER FORGE local development."""

import asyncio
from datetime import UTC, date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    Calculation,
    CalculationItem,
    CalculationStatus,
    CostType,
    Customer,
    Document,
    DocumentCategory,
    InboxClassification,
    InboxMessage,
    InboxStatus,
    Order,
    OrderItem,
    OrderPriority,
    OrderStatus,
    User,
    UserRole,
)


async def seed() -> None:
    """Create demo data."""
    async with AsyncSessionLocal() as db:
        # Check if data already exists
        from sqlalchemy import func, select

        count = (await db.execute(select(func.count()).select_from(Customer))).scalar()
        if count and count > 0:
            print(f"Database already has {count} customers, skipping seed.")
            return

        # --- Users ---
        users = [
            User(
                id=uuid4(),
                email="admin@infer.cz",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrátor",
                role=UserRole.ADMIN,
            ),
            User(
                id=uuid4(),
                email="novak@infer.cz",
                hashed_password=get_password_hash("heslo123"),
                full_name="Jan Novák",
                role=UserRole.OBCHODNIK,
                phone="+420 777 111 222",
            ),
            User(
                id=uuid4(),
                email="svoboda@infer.cz",
                hashed_password=get_password_hash("heslo123"),
                full_name="Petr Svoboda",
                role=UserRole.TECHNOLOG,
                phone="+420 777 333 444",
            ),
            User(
                id=uuid4(),
                email="vedeni@infer.cz",
                hashed_password=get_password_hash("heslo123"),
                full_name="Marie Vedoucí",
                role=UserRole.VEDENI,
            ),
            User(
                id=uuid4(),
                email="ucetni@infer.cz",
                hashed_password=get_password_hash("heslo123"),
                full_name="Eva Účetní",
                role=UserRole.UCETNI,
            ),
        ]
        db.add_all(users)
        await db.flush()

        # --- Customers ---
        customers = [
            Customer(
                id=uuid4(),
                company_name="ŠKODA AUTO a.s.",
                ico="00177041",
                dic="CZ00177041",
                contact_name="Jan Novák",
                email="jan.novak@skoda-auto.cz",
                phone="+420 326 811 111",
                address="tř. Václava Klementa 869, 293 01 Mladá Boleslav",
            ),
            Customer(
                id=uuid4(),
                company_name="ČEZ, a.s.",
                ico="45274649",
                dic="CZ45274649",
                contact_name="Petr Svoboda",
                email="petr.svoboda@cez.cz",
                phone="+420 211 041 111",
                address="Duhová 2/1444, 140 53 Praha 4",
            ),
            Customer(
                id=uuid4(),
                company_name="Siemens, s.r.o.",
                ico="00268577",
                dic="CZ00268577",
                contact_name="Marie Černá",
                email="marie.cerna@siemens.com",
                phone="+420 233 032 111",
                address="Siemensova 1, 155 00 Praha 13",
            ),
            Customer(
                id=uuid4(),
                company_name="Teplárna Liberec, a.s.",
                ico="62241672",
                dic="CZ62241672",
                contact_name="Tomáš Kříž",
                email="tomas.kriz@teplarna-liberec.cz",
                phone="+420 485 253 111",
                address="Dr. Milady Horákové 641/34, 460 01 Liberec",
            ),
            Customer(
                id=uuid4(),
                company_name="ARMATURY Group a.s.",
                ico="25836862",
                dic="CZ25836862",
                contact_name="Eva Dvořáková",
                email="eva.dvorakova@armatury.cz",
                phone="+420 595 133 111",
                address="Nádražní 120, 747 22 Dolní Benešov",
            ),
        ]
        db.add_all(customers)
        await db.flush()

        today = date.today()

        # --- Orders ---
        orders = [
            Order(
                id=uuid4(),
                customer_id=customers[0].id,
                number="ZAK-2026-001",
                status=OrderStatus.VYROBA,
                priority=OrderPriority.HIGH,
                due_date=today + timedelta(days=14),
                note="Svařované potrubní díly pro linku M1",
            ),
            Order(
                id=uuid4(),
                customer_id=customers[1].id,
                number="ZAK-2026-002",
                status=OrderStatus.NABIDKA,
                priority=OrderPriority.NORMAL,
                due_date=today + timedelta(days=45),
                note="Ocelová konstrukce pro tepelný výměník",
            ),
            Order(
                id=uuid4(),
                customer_id=customers[2].id,
                number="ZAK-2026-003",
                status=OrderStatus.OBJEDNAVKA,
                priority=OrderPriority.NORMAL,
                due_date=today + timedelta(days=30),
                note="Montáž průmyslového potrubí DN200",
            ),
            Order(
                id=uuid4(),
                customer_id=customers[3].id,
                number="ZAK-2026-004",
                status=OrderStatus.EXPEDICE,
                priority=OrderPriority.URGENT,
                due_date=today + timedelta(days=3),
                note="Náhradní díly pro kotel K3 — urgentní dodávka",
            ),
            Order(
                id=uuid4(),
                customer_id=customers[4].id,
                number="ZAK-2026-005",
                status=OrderStatus.POPTAVKA,
                priority=OrderPriority.LOW,
                due_date=today + timedelta(days=60),
                note="Armaturní sada PN40 pro novou halu",
            ),
            Order(
                id=uuid4(),
                customer_id=customers[0].id,
                number="ZAK-2026-006",
                status=OrderStatus.FAKTURACE,
                priority=OrderPriority.NORMAL,
                due_date=today - timedelta(days=5),
                note="Kolena 90° DN150 — dokončeno, k fakturaci",
            ),
            Order(
                id=uuid4(),
                customer_id=customers[1].id,
                number="ZAK-2026-007",
                status=OrderStatus.DOKONCENO,
                priority=OrderPriority.NORMAL,
                due_date=today - timedelta(days=20),
                note="Přechodové kusy pro parní rozvod — vyfakturováno",
            ),
            Order(
                id=uuid4(),
                customer_id=customers[2].id,
                number="ZAK-2026-008",
                status=OrderStatus.VYROBA,
                priority=OrderPriority.NORMAL,
                due_date=today + timedelta(days=21),
                note="T-kusy svařované DN300 PN25",
            ),
        ]
        db.add_all(orders)
        await db.flush()

        # --- Order Items ---
        items = [
            # ZAK-2026-001
            OrderItem(
                id=uuid4(),
                order_id=orders[0].id,
                name="Koleno 90° DN150 PN16",
                material="P265GH",
                quantity=Decimal("20"),
                unit="ks",
                dn="DN150",
                pn="PN16",
            ),
            OrderItem(
                id=uuid4(),
                order_id=orders[0].id,
                name="Přechod DN150/DN100",
                material="P265GH",
                quantity=Decimal("10"),
                unit="ks",
                dn="DN150",
            ),
            OrderItem(
                id=uuid4(),
                order_id=orders[0].id,
                name="T-kus DN150",
                material="P265GH",
                quantity=Decimal("5"),
                unit="ks",
                dn="DN150",
                pn="PN16",
            ),
            # ZAK-2026-002
            OrderItem(
                id=uuid4(),
                order_id=orders[1].id,
                name="Ocelový rám HEB 200",
                material="S355J2",
                quantity=Decimal("4"),
                unit="ks",
            ),
            OrderItem(
                id=uuid4(),
                order_id=orders[1].id,
                name="Nosník IPE 300",
                material="S355J2",
                quantity=Decimal("8"),
                unit="ks",
            ),
            # ZAK-2026-003
            OrderItem(
                id=uuid4(),
                order_id=orders[2].id,
                name="Potrubí bezešvé DN200",
                material="P235GH",
                quantity=Decimal("120"),
                unit="m",
                dn="DN200",
            ),
            OrderItem(
                id=uuid4(),
                order_id=orders[2].id,
                name="Příruba DN200 PN25",
                material="P250GH",
                quantity=Decimal("24"),
                unit="ks",
                dn="DN200",
                pn="PN25",
            ),
            # ZAK-2026-004
            OrderItem(
                id=uuid4(),
                order_id=orders[3].id,
                name="Potrubní oblouk DN250",
                material="16Mo3",
                quantity=Decimal("6"),
                unit="ks",
                dn="DN250",
            ),
            # ZAK-2026-008
            OrderItem(
                id=uuid4(),
                order_id=orders[7].id,
                name="T-kus DN300 PN25",
                material="P265GH",
                quantity=Decimal("12"),
                unit="ks",
                dn="DN300",
                pn="PN25",
            ),
            OrderItem(
                id=uuid4(),
                order_id=orders[7].id,
                name="Redukce DN300/DN200",
                material="P265GH",
                quantity=Decimal("6"),
                unit="ks",
                dn="DN300",
            ),
        ]
        db.add_all(items)
        await db.flush()

        # --- Calculations ---
        calc1 = Calculation(
            id=uuid4(),
            order_id=orders[0].id,
            name="Kalkulace ZAK-2026-001 — potrubní díly",
            status=CalculationStatus.APPROVED,
            margin_percent=Decimal("15"),
            material_total=Decimal("185000"),
            labor_total=Decimal("92000"),
            cooperation_total=Decimal("25000"),
            overhead_total=Decimal("18000"),
            margin_amount=Decimal("48000"),
            total_price=Decimal("368000"),
            note="Schválená kalkulace pro svařované díly",
        )
        calc2 = Calculation(
            id=uuid4(),
            order_id=orders[2].id,
            name="Kalkulace ZAK-2026-003 — montáž",
            status=CalculationStatus.DRAFT,
            margin_percent=Decimal("12"),
            material_total=Decimal("420000"),
            labor_total=Decimal("280000"),
            cooperation_total=Decimal("65000"),
            overhead_total=Decimal("45000"),
            margin_amount=Decimal("97200"),
            total_price=Decimal("907200"),
            note="Návrh — čeká na potvrzení materiálových cen",
        )
        calc3 = Calculation(
            id=uuid4(),
            order_id=orders[7].id,
            name="Kalkulace ZAK-2026-008 — T-kusy",
            status=CalculationStatus.OFFERED,
            margin_percent=Decimal("18"),
            material_total=Decimal("156000"),
            labor_total=Decimal("78000"),
            cooperation_total=Decimal("12000"),
            overhead_total=Decimal("14000"),
            margin_amount=Decimal("46800"),
            total_price=Decimal("306800"),
        )
        db.add_all([calc1, calc2, calc3])
        await db.flush()

        # --- Calculation Items ---
        calc_items = [
            CalculationItem(
                id=uuid4(),
                calculation_id=calc1.id,
                cost_type=CostType.MATERIAL,
                name="Ocelová trubka P265GH DN150",
                quantity=Decimal("35"),
                unit="m",
                unit_price=Decimal("3200"),
                total_price=Decimal("112000"),
            ),
            CalculationItem(
                id=uuid4(),
                calculation_id=calc1.id,
                cost_type=CostType.MATERIAL,
                name="Příruby P265GH DN150 PN16",
                quantity=Decimal("20"),
                unit="ks",
                unit_price=Decimal("3650"),
                total_price=Decimal("73000"),
            ),
            CalculationItem(
                id=uuid4(),
                calculation_id=calc1.id,
                cost_type=CostType.LABOR,
                name="Svařování WPS-01",
                quantity=Decimal("160"),
                unit="hod",
                unit_price=Decimal("450"),
                total_price=Decimal("72000"),
            ),
            CalculationItem(
                id=uuid4(),
                calculation_id=calc1.id,
                cost_type=CostType.LABOR,
                name="Broušení a povrchová úprava",
                quantity=Decimal("40"),
                unit="hod",
                unit_price=Decimal("500"),
                total_price=Decimal("20000"),
            ),
            CalculationItem(
                id=uuid4(),
                calculation_id=calc1.id,
                cost_type=CostType.COOPERATION,
                name="NDT kontrola — rentgen",
                quantity=Decimal("1"),
                unit="komplet",
                unit_price=Decimal("25000"),
                total_price=Decimal("25000"),
            ),
            CalculationItem(
                id=uuid4(),
                calculation_id=calc1.id,
                cost_type=CostType.OVERHEAD,
                name="Doprava na stavbu",
                quantity=Decimal("1"),
                unit="komplet",
                unit_price=Decimal("18000"),
                total_price=Decimal("18000"),
            ),
        ]
        db.add_all(calc_items)

        # --- Inbox Messages ---
        from datetime import datetime as dt

        now = dt.now(UTC)
        inbox_msgs = [
            InboxMessage(
                id=uuid4(),
                message_id=f"<msg-{uuid4().hex[:8]}@skoda-auto.cz>",
                from_email="jan.novak@skoda-auto.cz",
                subject="Poptávka — kolena DN150 PN16 pro linku M1",
                body_text="Dobrý den,\n\nzasíláme poptávku na 20 ks kolen 90° DN150 PN16 z materiálu P265GH.\nProsím o cenovou nabídku a termín dodání.\n\nS pozdravem,\nJan Novák",
                received_at=now - timedelta(hours=48),
                status=InboxStatus.PROCESSED,
                classification=InboxClassification.POPTAVKA,
                confidence=0.94,
                order_id=orders[0].id,
            ),
            InboxMessage(
                id=uuid4(),
                message_id=f"<msg-{uuid4().hex[:8]}@cez.cz>",
                from_email="petr.svoboda@cez.cz",
                subject="RE: Nabídka na ocelovou konstrukci tepelného výměníku",
                body_text="Dobrý den,\n\nděkujeme za nabídku č. NAB-2026-002. Prosíme o úpravu termínu.\n\nS pozdravem,\nPetr Svoboda",
                received_at=now - timedelta(hours=6),
                status=InboxStatus.NEW,
                classification=InboxClassification.OBJEDNAVKA,
                confidence=0.72,
            ),
            InboxMessage(
                id=uuid4(),
                message_id=f"<msg-{uuid4().hex[:8]}@siemens.com>",
                from_email="marie.cerna@siemens.com",
                subject="Reklamace — potrubní oblouk ZAK-2025-089",
                body_text="Dobrý den,\n\npři vstupní kontrole jsme zjistili odchylku v tloušťce stěny.\nProsím o řešení.\n\nDěkuji,\nMarie Černá",
                received_at=now - timedelta(hours=2),
                status=InboxStatus.NEW,
                classification=InboxClassification.REKLAMACE,
                confidence=0.88,
            ),
            InboxMessage(
                id=uuid4(),
                message_id=f"<msg-{uuid4().hex[:8]}@armatury.cz>",
                from_email="eva.dvorakova@armatury.cz",
                subject="Dotaz na materiálový atest 3.1 dle EN 10204",
                body_text="Dobrý den,\n\npotřebujeme materiálový atest 3.1 dle EN 10204 k objednávce ZAK-2026-005.\n\nDěkuji,\nEva Dvořáková",
                received_at=now - timedelta(minutes=30),
                status=InboxStatus.NEW,
                classification=InboxClassification.DOTAZ,
                confidence=0.65,
            ),
        ]
        db.add_all(inbox_msgs)

        # --- Documents ---
        docs = [
            Document(
                id=uuid4(),
                entity_type="order",
                entity_id=orders[0].id,
                file_name="vyrobni_vykres_ZAK-2026-001.pdf",
                file_path="/uploads/demo/vyrobni_vykres_ZAK-2026-001.pdf",
                mime_type="application/pdf",
                file_size=2450000,
                category=DocumentCategory.VYKRES,
                description="Výrobní výkres — kolena 90° DN150",
                version=1,
            ),
            Document(
                id=uuid4(),
                entity_type="order",
                entity_id=orders[0].id,
                file_name="WPS_01_P265GH.pdf",
                file_path="/uploads/demo/WPS_01_P265GH.pdf",
                mime_type="application/pdf",
                file_size=890000,
                category=DocumentCategory.WPS,
                description="WPS pro svařování P265GH",
                version=1,
            ),
            Document(
                id=uuid4(),
                entity_type="order",
                entity_id=orders[0].id,
                file_name="atestace_P265GH_EN10204.pdf",
                file_path="/uploads/demo/atestace_P265GH_EN10204.pdf",
                mime_type="application/pdf",
                file_size=1200000,
                category=DocumentCategory.ATESTACE,
                description="Materiálový certifikát 3.1 dle EN 10204",
                version=1,
            ),
            Document(
                id=uuid4(),
                entity_type="order",
                entity_id=orders[2].id,
                file_name="nabidka_ZAK-2026-003.xlsx",
                file_path="/uploads/demo/nabidka_ZAK-2026-003.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                file_size=185000,
                category=DocumentCategory.NABIDKA,
                description="Cenová nabídka na montáž DN200",
                version=2,
            ),
        ]
        db.add_all(docs)

        await db.commit()
        print(
            f"Seeded: {len(users)} users, {len(customers)} customers, {len(orders)} orders, "
            f"{len(items)} order items, 3 calculations, "
            f"{len(inbox_msgs)} inbox messages, {len(docs)} documents"
        )
        print("Login: admin@infer.cz / admin123")


if __name__ == "__main__":
    asyncio.run(seed())
