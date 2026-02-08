"""Seed realistic manufacturing data for INFER FORGE demos.

Adds 5 real engineering companies as customers, 8 manufacturing orders
with realistic pipe/steel items, 3 calculations, and 15 material prices.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.core.database import AsyncSessionLocal
from app.models import (
    Customer,
    Order,
    OrderItem,
)
from app.models.calculation import Calculation, CalculationItem, CalculationStatus, CostType
from app.models.order import OrderPriority, OrderStatus
from app.models.material_price import MaterialPrice


async def seed_manufacturing() -> None:
    """Create realistic manufacturing seed data."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func, select

        # Check if manufacturing data already exists
        count = (
            await db.execute(
                select(func.count()).select_from(Customer).where(Customer.ico == "24729035")
            )
        ).scalar()
        if count and count > 0:
            print("Manufacturing demo data already exists, skipping.")
            return

        print("Seeding manufacturing demo data...")

        # ── Customers (5 real companies) ──
        cez = Customer(
            id=uuid4(),
            company_name="ČEZ Distribuce a.s.",
            ico="24729035",
            dic="CZ24729035",
            email="obchod@cezdistribuce.cz",
            phone="+420 840 840 840",
            contact_name="Ing. Pavel Horák",
            address="Teplická 874/8\n405 02 Děčín",
            category="A",
            discount_percent=Decimal("5.00"),
            payment_terms_days=30,
        )
        vitkovice = Customer(
            id=uuid4(),
            company_name="Vítkovice Steel a.s.",
            ico="27801349",
            dic="CZ27801349",
            email="nabidky@vitkovicesteel.com",
            phone="+420 595 953 111",
            contact_name="Ing. Tomáš Krejčí",
            address="Ruská 2887/101\n706 02 Ostrava-Vítkovice",
            category="A",
            discount_percent=Decimal("3.00"),
            payment_terms_days=14,
        )
        unipetrol = Customer(
            id=uuid4(),
            company_name="ORLEN Unipetrol RPA s.r.o.",
            ico="27597075",
            dic="CZ27597075",
            email="procurement@unipetrol.cz",
            phone="+420 476 164 040",
            contact_name="Ing. Jana Dvořáková",
            address="Záluží 1\n436 70 Litvínov",
            category="B",
            discount_percent=Decimal("2.00"),
            payment_terms_days=21,
        )
        teplarna = Customer(
            id=uuid4(),
            company_name="Teplárny Brno a.s.",
            ico="46347534",
            dic="CZ46347534",
            email="technik@teplarny.cz",
            phone="+420 545 161 111",
            contact_name="Ing. Martin Veselý",
            address="Okružní 25\n638 00 Brno",
            category="B",
            discount_percent=Decimal("0.00"),
            payment_terms_days=14,
        )
        skoda = Customer(
            id=uuid4(),
            company_name="Škoda JS a.s.",
            ico="25235753",
            dic="CZ25235753",
            email="poptavky@skodajs.cz",
            phone="+420 378 041 111",
            contact_name="Ing. Radek Procházka",
            address="Orlík 266/15e\n316 06 Plzeň",
            category="A",
            discount_percent=Decimal("0.00"),
            payment_terms_days=30,
        )

        customers = [cez, vitkovice, unipetrol, teplarna, skoda]
        db.add_all(customers)
        await db.flush()
        print(f"  Created {len(customers)} customers")

        # ── Orders (8) ──
        today = date.today()

        order1 = Order(
            id=uuid4(),
            number="ZAK-2025-001",
            customer_id=cez.id,
            status=OrderStatus.VYROBA,
            priority=OrderPriority.HIGH,
            due_date=today + timedelta(days=42),
            note="T-kusy pro primární rozvod teplárny. Požadujeme 3.1 atestace.",
        )
        order1_items = [
            OrderItem(id=uuid4(), order_id=order1.id, name="T-kus DN200/100 PN16", material="P265GH", dn="200", pn="16", quantity=Decimal("5"), unit="ks", note="EN 10253-2, typ B"),
        ]

        order2 = Order(
            id=uuid4(),
            number="ZAK-2025-002",
            customer_id=vitkovice.id,
            status=OrderStatus.VYROBA,
            priority=OrderPriority.NORMAL,
            due_date=today + timedelta(days=28),
            note="Redukce pro rekonstrukci potrubního mostu.",
        )
        order2_items = [
            OrderItem(id=uuid4(), order_id=order2.id, name="Redukce DN150/100", material="P235GH", dn="150", pn="16", quantity=Decimal("12"), unit="ks", note="EN 10253-2, soustředná"),
        ]

        order3 = Order(
            id=uuid4(),
            number="ZAK-2025-003",
            customer_id=unipetrol.id,
            status=OrderStatus.NABIDKA,
            priority=OrderPriority.HIGH,
            due_date=today + timedelta(days=56),
            note="Ohyby pro petrochemický provoz. Žáruvzdorný materiál.",
        )
        order3_items = [
            OrderItem(id=uuid4(), order_id=order3.id, name="Svařovaný ohyb 90° DN300", material="16Mo3", dn="300", pn="25", quantity=Decimal("3"), unit="ks", note="EN 10253-2, R=1.5D"),
        ]

        order4 = Order(
            id=uuid4(),
            number="ZAK-2025-004",
            customer_id=teplarna.id,
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.NORMAL,
            due_date=today + timedelta(days=63),
            note="Kompenzátory pro tepelný roztah parovodního potrubí.",
        )
        order4_items = [
            OrderItem(id=uuid4(), order_id=order4.id, name="Kompenzátor DN250 PN25", material="1.4541", dn="250", pn="25", quantity=Decimal("2"), unit="ks", note="Vlnovcový, axiální, nerez"),
        ]

        order5 = Order(
            id=uuid4(),
            number="ZAK-2025-005",
            customer_id=cez.id,
            status=OrderStatus.VYROBA,
            priority=OrderPriority.HIGH,
            due_date=today + timedelta(days=90),
            note="Potrubní most pro nadzemní vedení parovodu. Kompletní dodávka vč. montáže.",
        )
        order5_items = [
            OrderItem(id=uuid4(), order_id=order5.id, name="Potrubní most 12m", material="S355J2", dn="", pn="", quantity=Decimal("1"), unit="ks", note="Včetně OK konstrukce, nátěru a montáže"),
            OrderItem(id=uuid4(), order_id=order5.id, name="Nosný sloup HEB 200", material="S355J2", dn="", pn="", quantity=Decimal("4"), unit="ks", note="Kotvení chemickými kotvami"),
            OrderItem(id=uuid4(), order_id=order5.id, name="Izolace potrubí DN200", material="minerální vlna", dn="200", pn="", quantity=Decimal("24"), unit="m", note="Tl. 80mm, Al plášť"),
        ]

        order6 = Order(
            id=uuid4(),
            number="ZAK-2025-006",
            customer_id=skoda.id,
            status=OrderStatus.NABIDKA,
            priority=OrderPriority.URGENT,
            due_date=today + timedelta(days=120),
            note="Plášť výměníku tepla dle výkresové dokumentace. NDT 100%.",
        )
        order6_items = [
            OrderItem(id=uuid4(), order_id=order6.id, name="Plášť výměníku tepla DN500", material="P265GH", dn="500", pn="40", quantity=Decimal("1"), unit="ks", note="Tl. stěny 16mm, délka 3200mm"),
        ]

        order7 = Order(
            id=uuid4(),
            number="ZAK-2025-007",
            customer_id=vitkovice.id,
            status=OrderStatus.DOKONCENO,
            priority=OrderPriority.LOW,
            due_date=today - timedelta(days=7),
            note="Standardní kolena ze skladu. Dodáno.",
        )
        order7_items = [
            OrderItem(id=uuid4(), order_id=order7.id, name="Koleno 45° DN100 PN16", material="P235GH", dn="100", pn="16", quantity=Decimal("20"), unit="ks", note="EN 10253-2"),
        ]

        order8 = Order(
            id=uuid4(),
            number="ZAK-2025-008",
            customer_id=unipetrol.id,
            status=OrderStatus.OBJEDNAVKA,
            priority=OrderPriority.NORMAL,
            due_date=today + timedelta(days=35),
            note="Příruby pro výměnu na jednotce krakování.",
        )
        order8_items = [
            OrderItem(id=uuid4(), order_id=order8.id, name="Příruba DN200 PN40", material="11 353", dn="200", pn="40", quantity=Decimal("50"), unit="ks", note="EN 1092-1, typ 11, kovaná"),
        ]

        orders = [order1, order2, order3, order4, order5, order6, order7, order8]
        all_items = order1_items + order2_items + order3_items + order4_items + order5_items + order6_items + order7_items + order8_items
        db.add_all(orders)
        db.add_all(all_items)
        await db.flush()
        print(f"  Created {len(orders)} orders with {len(all_items)} items")

        # ── Calculations (3) ──
        # ZAK-2025-001: T-kus DN200/100 PN16, 5 ks
        calc1 = Calculation(
            id=uuid4(),
            order_id=order1.id,
            version=1,
            status=CalculationStatus.APPROVED,
            margin_percent=Decimal("15.0"),
            total_price=Decimal("97750.00"),
            notes="Kalkulace schválena vedením 2025-01-15. Materiál P265GH ze skladu.",
        )
        calc1_items = [
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.MATERIAL, name="Plech P265GH tl.12mm", unit="t", quantity=Decimal("0.35"), unit_price=Decimal("28500.00"), total_price=Decimal("9975.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.MATERIAL, name="Trubka TR 219,1x6,3 P265GH", unit="m", quantity=Decimal("5.0"), unit_price=Decimal("1250.00"), total_price=Decimal("6250.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.MATERIAL, name="Trubka TR 114,3x3,6 P265GH", unit="m", quantity=Decimal("3.0"), unit_price=Decimal("385.00"), total_price=Decimal("1155.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.MATERIAL, name="Svařovací materiál OK 48.00", unit="kg", quantity=Decimal("8.0"), unit_price=Decimal("145.00"), total_price=Decimal("1160.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.LABOR, name="Řezání a příprava", unit="hod", quantity=Decimal("8.0"), unit_price=Decimal("850.00"), total_price=Decimal("6800.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.LABOR, name="Svařování (141+111)", unit="hod", quantity=Decimal("16.0"), unit_price=Decimal("950.00"), total_price=Decimal("15200.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.LABOR, name="Dokončení, tryskání", unit="hod", quantity=Decimal("4.0"), unit_price=Decimal("750.00"), total_price=Decimal("3000.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.COOPERATION, name="NDT - RT kontrola svarů", unit="ks", quantity=Decimal("5.0"), unit_price=Decimal("1200.00"), total_price=Decimal("6000.00")),
            CalculationItem(id=uuid4(), calculation_id=calc1.id, cost_type=CostType.OVERHEAD, name="Režie výroby 15%", unit="ks", quantity=Decimal("1.0"), unit_price=Decimal("7481.00"), total_price=Decimal("7481.00")),
        ]

        # ZAK-2025-002: Redukce DN150/100, 12 ks
        calc2 = Calculation(
            id=uuid4(),
            order_id=order2.id,
            version=1,
            status=CalculationStatus.APPROVED,
            margin_percent=Decimal("12.0"),
            total_price=Decimal("58240.00"),
            notes="Sériová výroba, sleva na materiálu.",
        )
        calc2_items = [
            CalculationItem(id=uuid4(), calculation_id=calc2.id, cost_type=CostType.MATERIAL, name="Trubka TR 168,3x4,5 P235GH", unit="m", quantity=Decimal("8.0"), unit_price=Decimal("680.00"), total_price=Decimal("5440.00")),
            CalculationItem(id=uuid4(), calculation_id=calc2.id, cost_type=CostType.MATERIAL, name="Trubka TR 114,3x3,6 P235GH", unit="m", quantity=Decimal("6.0"), unit_price=Decimal("385.00"), total_price=Decimal("2310.00")),
            CalculationItem(id=uuid4(), calculation_id=calc2.id, cost_type=CostType.MATERIAL, name="Svařovací materiál", unit="kg", quantity=Decimal("5.0"), unit_price=Decimal("145.00"), total_price=Decimal("725.00")),
            CalculationItem(id=uuid4(), calculation_id=calc2.id, cost_type=CostType.LABOR, name="Řezání + kalibrace", unit="hod", quantity=Decimal("6.0"), unit_price=Decimal("850.00"), total_price=Decimal("5100.00")),
            CalculationItem(id=uuid4(), calculation_id=calc2.id, cost_type=CostType.LABOR, name="Svařování", unit="hod", quantity=Decimal("10.0"), unit_price=Decimal("950.00"), total_price=Decimal("9500.00")),
            CalculationItem(id=uuid4(), calculation_id=calc2.id, cost_type=CostType.OVERHEAD, name="Režie výroby 12%", unit="ks", quantity=Decimal("1.0"), unit_price=Decimal("2769.00"), total_price=Decimal("2769.00")),
        ]

        # ZAK-2025-005: Potrubní most 12m
        calc5 = Calculation(
            id=uuid4(),
            order_id=order5.id,
            version=1,
            status=CalculationStatus.APPROVED,
            margin_percent=Decimal("18.0"),
            total_price=Decimal("485100.00"),
            notes="Kompletní dodávka vč. OK konstrukce a montáže. Cena dle nabídky ČEZ.",
        )
        calc5_items = [
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.MATERIAL, name="Profily HEB 200, IPE 200", unit="t", quantity=Decimal("2.8"), unit_price=Decimal("32000.00"), total_price=Decimal("89600.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.MATERIAL, name="Plechy S355J2, styčníky", unit="t", quantity=Decimal("0.6"), unit_price=Decimal("28000.00"), total_price=Decimal("16800.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.MATERIAL, name="Trubky DN200 P265GH", unit="m", quantity=Decimal("14.0"), unit_price=Decimal("1250.00"), total_price=Decimal("17500.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.MATERIAL, name="Izolace + oplechování", unit="m", quantity=Decimal("24.0"), unit_price=Decimal("850.00"), total_price=Decimal("20400.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.MATERIAL, name="Spojovací materiál, kotvy", unit="sada", quantity=Decimal("1.0"), unit_price=Decimal("8500.00"), total_price=Decimal("8500.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.MATERIAL, name="Svařovací materiál", unit="kg", quantity=Decimal("35.0"), unit_price=Decimal("180.00"), total_price=Decimal("6300.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.LABOR, name="Dílna — výroba OK", unit="hod", quantity=Decimal("60.0"), unit_price=Decimal("850.00"), total_price=Decimal("51000.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.LABOR, name="Dílna — svařování potrubí", unit="hod", quantity=Decimal("40.0"), unit_price=Decimal("950.00"), total_price=Decimal("38000.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.LABOR, name="Montáž na stavbě", unit="hod", quantity=Decimal("80.0"), unit_price=Decimal("1100.00"), total_price=Decimal("88000.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.COOPERATION, name="NDT kontrola svarů", unit="ks", quantity=Decimal("8.0"), unit_price=Decimal("1500.00"), total_price=Decimal("12000.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.COOPERATION, name="Povrchová úprava — tryskání + nátěr", unit="m2", quantity=Decimal("45.0"), unit_price=Decimal("350.00"), total_price=Decimal("15750.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.COOPERATION, name="Doprava nadrozměr", unit="ks", quantity=Decimal("1.0"), unit_price=Decimal("18000.00"), total_price=Decimal("18000.00")),
            CalculationItem(id=uuid4(), calculation_id=calc5.id, cost_type=CostType.OVERHEAD, name="Režie 18% (dokumentace, PD, řízení)", unit="ks", quantity=Decimal("1.0"), unit_price=Decimal("68850.00"), total_price=Decimal("68850.00")),
        ]

        calcs = [calc1, calc2, calc5]
        all_calc_items = calc1_items + calc2_items + calc5_items
        db.add_all(calcs)
        db.add_all(all_calc_items)
        await db.flush()
        print(f"  Created {len(calcs)} calculations with {len(all_calc_items)} items")

        # ── Material Prices (15) ──
        material_prices = [
            MaterialPrice(id=uuid4(), name="Trubka bezešvá TR 114,3x3,6 P235GH", specification="EN 10216-2", material_grade="P235GH", form="trubka", dimension="114,3x3,6mm", unit="m", unit_price=Decimal("385.00"), supplier="Železárny Hrádek a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Trubka bezešvá TR 219,1x6,3 P265GH", specification="EN 10216-2", material_grade="P265GH", form="trubka", dimension="219,1x6,3mm", unit="m", unit_price=Decimal("1250.00"), supplier="ArcelorMittal Ostrava a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Trubka bezešvá TR 323,9x8,0 16Mo3", specification="EN 10216-2, žáruvzdorná", material_grade="16Mo3", form="trubka", dimension="323,9x8,0mm", unit="m", unit_price=Decimal("2850.00"), supplier="Salzgitter Mannesmann", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Plech P265GH tl.10mm", specification="EN 10028-2, šířka 2000mm", material_grade="P265GH", form="plech", dimension="10x2000mm", unit="t", unit_price=Decimal("28500.00"), supplier="ArcelorMittal Ostrava a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Plech S355J2 tl.20mm", specification="EN 10025-2, šířka 2500mm", material_grade="S355J2", form="plech", dimension="20x2500mm", unit="t", unit_price=Decimal("24800.00"), supplier="ArcelorMittal Ostrava a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Příruba PN16 DN100 P250GH", specification="EN 1092-1, typ 11", material_grade="P250GH", form="příruba", dimension="DN100", unit="ks", unit_price=Decimal("1250.00"), supplier="MZ Liberec a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Příruba PN16 DN200 P250GH", specification="EN 1092-1, typ 11", material_grade="P250GH", form="příruba", dimension="DN200", unit="ks", unit_price=Decimal("1850.00"), supplier="MZ Liberec a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Příruba PN25 DN150 11 353", specification="EN 1092-1, typ 01", material_grade="11 353", form="příruba", dimension="DN150", unit="ks", unit_price=Decimal("2100.00"), supplier="KOVOSVIT", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Profil IPE 200 S355J2", specification="EN 10025-2", material_grade="S355J2", form="profil", dimension="IPE 200", unit="m", unit_price=Decimal("1380.00"), supplier="Ferona a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Profil HEB 160 S355J2", specification="EN 10025-2", material_grade="S355J2", form="profil", dimension="HEB 160", unit="m", unit_price=Decimal("1650.00"), supplier="Ferona a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Úhelník L 80x80x8 S235JR", specification="EN 10056-1", material_grade="S235JR", form="profil", dimension="80x80x8mm", unit="m", unit_price=Decimal("420.00"), supplier="Ferona a.s.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Elektroda OK 48.00 3,2mm", specification="EN ISO 2560-A, bazická", material_grade="", form="svařovací materiál", dimension="3,2mm", unit="kg", unit_price=Decimal("145.00"), supplier="ESAB Vamberk s.r.o.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Drát OK Tigrod 12.64 2,0mm", specification="EN ISO 636-A, pro 16Mo3", material_grade="", form="svařovací materiál", dimension="2,0mm", unit="kg", unit_price=Decimal("320.00"), supplier="ESAB Vamberk s.r.o.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Šroub M16x60 pevnost 8.8 pozink", specification="EN ISO 4014", material_grade="8.8", form="spojovací materiál", dimension="M16x60", unit="ks", unit_price=Decimal("12.50"), supplier="BOSSARD CZ s.r.o.", valid_from=today - timedelta(days=30), is_active=True),
            MaterialPrice(id=uuid4(), name="Trubka nerez TR 108,0x5,0 1.4541", specification="EN 10216-5, stabilizovaná Ti", material_grade="1.4541", form="trubka", dimension="108,0x5,0mm", unit="m", unit_price=Decimal("2850.00"), supplier="ITALINOX s.r.o.", valid_from=today - timedelta(days=30), is_active=True),
        ]

        db.add_all(material_prices)
        await db.flush()
        print(f"  Created {len(material_prices)} material prices")

        await db.commit()
        print("Manufacturing demo data seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_manufacturing())
