"""Seed additional demo data for tables that are empty on the server.

Supplements seed_demo.py with: material_prices, subcontractors, subcontracts,
operations, offers, user_points, notifications.
Also updates customer categories/discounts.
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models import (
    Customer,
    MaterialPrice,
    Notification,
    NotificationType,
    Offer,
    OfferStatus,
    Operation,
    OperationStatus,
    Order,
    PointsAction,
    Subcontract,
    Subcontractor,
    User,
    UserPoints,
)


async def seed_additional() -> None:
    """Seed data for empty tables, referencing existing orders/users/customers."""
    async with AsyncSessionLocal() as db:
        # --- Load existing entities ---
        users = (await db.execute(select(User).order_by(User.email))).scalars().all()
        customers = (await db.execute(select(Customer).order_by(Customer.company_name))).scalars().all()
        orders = (await db.execute(select(Order).order_by(Order.number))).scalars().all()

        if not users or not orders:
            print("No existing data found. Run seed_demo.py first.")
            return

        print(f"Found {len(users)} users, {len(customers)} customers, {len(orders)} orders")
        today = date.today()
        now = datetime.now(UTC)

        # Map by email/name for easy reference
        user_map = {u.email: u for u in users}
        admin = user_map.get("admin@infer.cz", users[0])
        obchodnik = user_map.get("novak@infer.cz", users[1] if len(users) > 1 else users[0])
        technolog = user_map.get("svoboda@infer.cz", users[2] if len(users) > 2 else users[0])
        vedeni = user_map.get("vedeni@infer.cz", users[3] if len(users) > 3 else users[0])

        # =====================================================================
        # 1. MATERIAL PRICES (ceník materiálů — reálné strojírenské ceny)
        # =====================================================================
        count = (await db.execute(select(func.count()).select_from(MaterialPrice))).scalar()
        if count and count > 0:
            print(f"  material_prices: already has {count} rows, skipping")
        else:
            materials = [
                # Plechy
                MaterialPrice(
                    id=uuid4(), name="Ocel S235JR plech 10mm",
                    specification="EN 10025-2, tl. 10mm, 1000x2000mm",
                    material_grade="S235JR", form="plech", dimension="10x1000x2000mm",
                    unit="kg", unit_price=Decimal("28.50"),
                    supplier="Ferona a.s.", valid_from=today - timedelta(days=30),
                    is_active=True, notes="Standardní konstrukční ocel",
                ),
                MaterialPrice(
                    id=uuid4(), name="Ocel S355J2 plech 15mm",
                    specification="EN 10025-2, tl. 15mm, 1500x3000mm",
                    material_grade="S355J2", form="plech", dimension="15x1500x3000mm",
                    unit="kg", unit_price=Decimal("32.80"),
                    supplier="Ferona a.s.", valid_from=today - timedelta(days=30),
                    is_active=True,
                ),
                MaterialPrice(
                    id=uuid4(), name="Ocel S355J2 plech 20mm",
                    specification="EN 10025-2, tl. 20mm, 1500x3000mm",
                    material_grade="S355J2", form="plech", dimension="20x1500x3000mm",
                    unit="kg", unit_price=Decimal("33.50"),
                    supplier="ArcelorMittal", valid_from=today - timedelta(days=15),
                    is_active=True,
                ),
                # Trubky
                MaterialPrice(
                    id=uuid4(), name="Trubka P265GH DN100",
                    specification="EN 10216-2, bezešvá, tl. 4.5mm",
                    material_grade="P265GH", form="trubka", dimension="DN100 (114.3x4.5mm)",
                    unit="m", unit_price=Decimal("850.00"),
                    supplier="Železárny Podbrezová", valid_from=today - timedelta(days=60),
                    is_active=True, notes="Pro tlakové aplikace do 400°C",
                ),
                MaterialPrice(
                    id=uuid4(), name="Trubka P265GH DN150",
                    specification="EN 10216-2, bezešvá, tl. 5.0mm",
                    material_grade="P265GH", form="trubka", dimension="DN150 (168.3x5.0mm)",
                    unit="m", unit_price=Decimal("1250.00"),
                    supplier="Železárny Podbrezová", valid_from=today - timedelta(days=60),
                    is_active=True,
                ),
                MaterialPrice(
                    id=uuid4(), name="Trubka P265GH DN200",
                    specification="EN 10216-2, bezešvá, tl. 6.3mm",
                    material_grade="P265GH", form="trubka", dimension="DN200 (219.1x6.3mm)",
                    unit="m", unit_price=Decimal("1850.00"),
                    supplier="Železárny Podbrezová", valid_from=today - timedelta(days=60),
                    is_active=True,
                ),
                MaterialPrice(
                    id=uuid4(), name="Trubka P235GH DN200",
                    specification="EN 10217-2, svařovaná, tl. 5.0mm",
                    material_grade="P235GH", form="trubka", dimension="DN200 (219.1x5.0mm)",
                    unit="m", unit_price=Decimal("1420.00"),
                    supplier="Ferona a.s.", valid_from=today - timedelta(days=45),
                    is_active=True,
                ),
                MaterialPrice(
                    id=uuid4(), name="Trubka 16Mo3 DN250",
                    specification="EN 10216-2, bezešvá, tl. 8.0mm",
                    material_grade="16Mo3", form="trubka", dimension="DN250 (273.0x8.0mm)",
                    unit="m", unit_price=Decimal("3200.00"),
                    supplier="Salzgitter Mannesmann", valid_from=today - timedelta(days=30),
                    is_active=True, notes="Žáropevná ocel pro teploty do 530°C",
                ),
                # Profily
                MaterialPrice(
                    id=uuid4(), name="Profil HEB 200",
                    specification="EN 10025-2, S355J2",
                    material_grade="S355J2", form="profil", dimension="HEB 200",
                    unit="m", unit_price=Decimal("2450.00"),
                    supplier="ArcelorMittal", valid_from=today - timedelta(days=20),
                    is_active=True,
                ),
                MaterialPrice(
                    id=uuid4(), name="Profil IPE 300",
                    specification="EN 10025-2, S355J2",
                    material_grade="S355J2", form="profil", dimension="IPE 300",
                    unit="m", unit_price=Decimal("2180.00"),
                    supplier="ArcelorMittal", valid_from=today - timedelta(days=20),
                    is_active=True,
                ),
                # Příruby
                MaterialPrice(
                    id=uuid4(), name="Příruba DN150 PN16",
                    specification="EN 1092-1, typ 01, P265GH",
                    material_grade="P265GH", form="příruba", dimension="DN150 PN16",
                    unit="ks", unit_price=Decimal("1850.00"),
                    supplier="Interflange", valid_from=today - timedelta(days=30),
                    is_active=True,
                ),
                MaterialPrice(
                    id=uuid4(), name="Příruba DN200 PN25",
                    specification="EN 1092-1, typ 11, P250GH",
                    material_grade="P250GH", form="příruba", dimension="DN200 PN25",
                    unit="ks", unit_price=Decimal("2650.00"),
                    supplier="Interflange", valid_from=today - timedelta(days=30),
                    is_active=True,
                ),
                MaterialPrice(
                    id=uuid4(), name="Příruba DN300 PN25",
                    specification="EN 1092-1, typ 11, P265GH",
                    material_grade="P265GH", form="příruba", dimension="DN300 PN25",
                    unit="ks", unit_price=Decimal("4200.00"),
                    supplier="Interflange", valid_from=today - timedelta(days=15),
                    is_active=True,
                ),
                # Svařovací materiál
                MaterialPrice(
                    id=uuid4(), name="Svařovací drát OK Autrod 12.51 ø1.2mm",
                    specification="EN ISO 14341-A, G 42 4 M G3Si1",
                    material_grade="G3Si1", form="svařovací materiál", dimension="ø1.2mm, cívka 18kg",
                    unit="kg", unit_price=Decimal("65.00"),
                    supplier="ESAB", valid_from=today - timedelta(days=90),
                    is_active=True, notes="MAG svařování, běžná ocel",
                ),
                MaterialPrice(
                    id=uuid4(), name="Elektrody E-B 121 ø3.2mm",
                    specification="EN ISO 2560-A, E 42 4 B 42 H5",
                    material_grade="E-B 121", form="svařovací materiál", dimension="ø3.2x350mm",
                    unit="kg", unit_price=Decimal("95.00"),
                    supplier="ESAB", valid_from=today - timedelta(days=90),
                    is_active=True, notes="Bazické elektrody pro P265GH",
                ),
                # Ochranný plyn
                MaterialPrice(
                    id=uuid4(), name="Ochranný plyn M21 (Ar/CO2 82/18)",
                    specification="EN ISO 14175, M21-ArC-18",
                    material_grade=None, form="plyn", dimension="lahev 50L",
                    unit="lahev", unit_price=Decimal("2800.00"),
                    supplier="Linde Gas", valid_from=today - timedelta(days=120),
                    is_active=True,
                ),
                # Neaktivní (stará cena)
                MaterialPrice(
                    id=uuid4(), name="Ocel S235JR plech 10mm",
                    specification="EN 10025-2, tl. 10mm, 1000x2000mm",
                    material_grade="S235JR", form="plech", dimension="10x1000x2000mm",
                    unit="kg", unit_price=Decimal("25.80"),
                    supplier="Ferona a.s.", valid_from=today - timedelta(days=365),
                    valid_to=today - timedelta(days=31),
                    is_active=False, notes="Stará cena — nahrazena aktuální",
                ),
            ]
            db.add_all(materials)
            await db.flush()
            print(f"  material_prices: seeded {len(materials)} items")

        # =====================================================================
        # 2. SUBCONTRACTORS (subdodavatelé)
        # =====================================================================
        count = (await db.execute(select(func.count()).select_from(Subcontractor))).scalar()
        if count and count > 0:
            print(f"  subcontractors: already has {count} rows, skipping")
            subcontractors = (await db.execute(select(Subcontractor))).scalars().all()
        else:
            subcontractors = [
                Subcontractor(
                    id=uuid4(), name="NDT Servis s.r.o.",
                    ico="26847523", contact_email="info@ndt-servis.cz",
                    contact_phone="+420 596 241 111",
                    specialization="NDT kontrola",
                    rating=5, is_active=True,
                    notes="Certifikovaná NDT laboratoř — RT, UT, MT, PT. Akreditace ČIA.",
                ),
                Subcontractor(
                    id=uuid4(), name="Povrchové úpravy Ostrava s.r.o.",
                    ico="28631845", contact_email="obchod@povrchove-upravy.cz",
                    contact_phone="+420 596 318 222",
                    specialization="Povrchová úprava",
                    rating=4, is_active=True,
                    notes="Tryskání Sa 2.5, žárový zinek, nátěry dle ISO 12944",
                ),
                Subcontractor(
                    id=uuid4(), name="TRANSPORTSERVIS Morava a.s.",
                    ico="25368974", contact_email="doprava@transportservis.cz",
                    contact_phone="+420 585 412 333",
                    specialization="Doprava a logistika",
                    rating=4, is_active=True,
                    notes="Nadrozměrná přeprava, jeřábnické práce, montážní plošiny",
                ),
                Subcontractor(
                    id=uuid4(), name="CNC Obrábění Frýdek s.r.o.",
                    ico="27156432", contact_email="cnc@obrabeni-frydek.cz",
                    contact_phone="+420 558 632 444",
                    specialization="CNC obrábění",
                    rating=5, is_active=True,
                    notes="Přesné obrábění přírub, hrdel, přechodů. CNC soustruh max ø800mm.",
                ),
                Subcontractor(
                    id=uuid4(), name="Tepelné zpracování Třinec s.r.o.",
                    ico="29451278", contact_email="pece@tz-trinec.cz",
                    contact_phone="+420 558 531 555",
                    specialization="Tepelné zpracování",
                    rating=3, is_active=True,
                    notes="Žíhání ke snížení pnutí, normalizační žíhání, popouštění. Max 8m.",
                ),
                Subcontractor(
                    id=uuid4(), name="KOVOMONT Šumperk",
                    ico="15478963", contact_email="kovomont@seznam.cz",
                    contact_phone="+420 583 214 666",
                    specialization="Montáž",
                    rating=3, is_active=False,
                    notes="Pozastavena spolupráce — kvalitativní problémy Q1/2026",
                ),
            ]
            db.add_all(subcontractors)
            await db.flush()
            print(f"  subcontractors: seeded {len(subcontractors)} items")

        # =====================================================================
        # 3. SUBCONTRACTS (kooperace — vazba subdodavatel × zakázka)
        # =====================================================================
        count = (await db.execute(select(func.count()).select_from(Subcontract))).scalar()
        if count and count > 0:
            print(f"  subcontracts: already has {count} rows, skipping")
        else:
            active_subs = [s for s in subcontractors if s.is_active]
            subcontracts = [
                # ZAK-2026-001: NDT kontrola svařů
                Subcontract(
                    id=uuid4(), order_id=orders[0].id,
                    subcontractor_id=active_subs[0].id,  # NDT Servis
                    description="RT kontrola svarů kolen DN150 — 100% rozsah dle EN 13480-5",
                    price=Decimal("25000.00"), status="completed",
                    planned_start=now - timedelta(days=5),
                    planned_end=now - timedelta(days=3),
                    actual_end=now - timedelta(days=3),
                    notes="Protokol č. NDT-2026-0145, všechny svary OK",
                ),
                # ZAK-2026-001: Povrchová úprava
                Subcontract(
                    id=uuid4(), order_id=orders[0].id,
                    subcontractor_id=active_subs[1].id,  # Povrchové úpravy
                    description="Tryskání Sa 2.5 + základní nátěr dle ISO 12944 C4",
                    price=Decimal("18500.00"), status="in_progress",
                    planned_start=now - timedelta(days=1),
                    planned_end=now + timedelta(days=2),
                ),
                # ZAK-2026-003: Doprava na stavbu
                Subcontract(
                    id=uuid4(), order_id=orders[2].id,
                    subcontractor_id=active_subs[2].id,  # TRANSPORTSERVIS
                    description="Přeprava potrubí DN200 na stavbu + jeřáb pro vykládku",
                    price=Decimal("35000.00"), status="confirmed",
                    planned_start=now + timedelta(days=20),
                    planned_end=now + timedelta(days=21),
                ),
                # ZAK-2026-008: CNC obrábění přírubových hrdel
                Subcontract(
                    id=uuid4(), order_id=orders[7].id,
                    subcontractor_id=active_subs[3].id,  # CNC Frýdek
                    description="CNC obrábění přírubových hrdel T-kusů DN300 — tolerance H7",
                    price=Decimal("42000.00"), status="in_progress",
                    planned_start=now - timedelta(days=3),
                    planned_end=now + timedelta(days=4),
                    notes="Materiál dodán 5.2., zahájeno obrábění",
                ),
                # ZAK-2026-008: Tepelné zpracování
                Subcontract(
                    id=uuid4(), order_id=orders[7].id,
                    subcontractor_id=active_subs[4].id,  # TZ Třinec
                    description="Žíhání ke snížení pnutí po svařování — T-kusy DN300",
                    price=Decimal("15000.00"), status="requested",
                    planned_start=now + timedelta(days=7),
                    planned_end=now + timedelta(days=9),
                ),
            ]
            db.add_all(subcontracts)
            await db.flush()
            print(f"  subcontracts: seeded {len(subcontracts)} items")

        # =====================================================================
        # 4. OPERATIONS (výrobní operace)
        # =====================================================================
        count = (await db.execute(select(func.count()).select_from(Operation))).scalar()
        if count and count > 0:
            print(f"  operations: already has {count} rows, skipping")
        else:
            operations = [
                # ZAK-2026-001 (VYROBA) — 6 operací
                Operation(
                    id=uuid4(), order_id=orders[0].id,
                    name="Řezání materiálu", sequence=1,
                    description="Dělení trubek P265GH DN150 na pásové pile",
                    duration_hours=Decimal("8.0"), responsible="Petr Svoboda",
                    planned_start=now - timedelta(days=10),
                    planned_end=now - timedelta(days=9),
                    actual_start=now - timedelta(days=10),
                    actual_end=now - timedelta(days=9),
                    status=OperationStatus.COMPLETED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[0].id,
                    name="Tváření — lisování kolen", sequence=2,
                    description="Lisování kolen 90° DN150 za tepla",
                    duration_hours=Decimal("16.0"), responsible="Petr Svoboda",
                    planned_start=now - timedelta(days=9),
                    planned_end=now - timedelta(days=7),
                    actual_start=now - timedelta(days=9),
                    actual_end=now - timedelta(days=7),
                    status=OperationStatus.COMPLETED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[0].id,
                    name="Svařování WPS-01", sequence=3,
                    description="Obvodové svary dle WPS-01, svářeč cert. EN ISO 9606-1",
                    duration_hours=Decimal("40.0"), responsible="Petr Svoboda",
                    planned_start=now - timedelta(days=7),
                    planned_end=now - timedelta(days=2),
                    actual_start=now - timedelta(days=7),
                    status=OperationStatus.IN_PROGRESS.value,
                    notes="Svařování v procesu, hotovo 70%",
                ),
                Operation(
                    id=uuid4(), order_id=orders[0].id,
                    name="NDT kontrola", sequence=4,
                    description="RT kontrola 100% svarů dle EN 13480-5 (kooperace NDT Servis)",
                    duration_hours=Decimal("8.0"), responsible="NDT Servis s.r.o.",
                    planned_start=now + timedelta(days=1),
                    planned_end=now + timedelta(days=2),
                    status=OperationStatus.PLANNED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[0].id,
                    name="Povrchová úprava", sequence=5,
                    description="Tryskání Sa 2.5, základní nátěr ISO 12944 C4",
                    duration_hours=Decimal("12.0"), responsible="Povrchové úpravy Ostrava",
                    planned_start=now + timedelta(days=3),
                    planned_end=now + timedelta(days=5),
                    status=OperationStatus.PLANNED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[0].id,
                    name="Výstupní kontrola + balení", sequence=6,
                    description="Rozměrová kontrola, materiálový atest 3.1, balení pro přepravu",
                    duration_hours=Decimal("4.0"), responsible="Petr Svoboda",
                    planned_start=now + timedelta(days=6),
                    planned_end=now + timedelta(days=6),
                    status=OperationStatus.PLANNED.value,
                ),
                # ZAK-2026-003 (OBJEDNAVKA) — 4 operace (plánované)
                Operation(
                    id=uuid4(), order_id=orders[2].id,
                    name="Příjem materiálu", sequence=1,
                    description="Vstupní kontrola trubek DN200 P235GH, ověření atestů",
                    duration_hours=Decimal("4.0"), responsible="Petr Svoboda",
                    planned_start=now + timedelta(days=5),
                    planned_end=now + timedelta(days=5),
                    status=OperationStatus.PLANNED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[2].id,
                    name="Předvýroba — řezání + úkosy", sequence=2,
                    description="Řezání trubek + příprava svarových úkosů",
                    duration_hours=Decimal("24.0"), responsible="Petr Svoboda",
                    planned_start=now + timedelta(days=6),
                    planned_end=now + timedelta(days=9),
                    status=OperationStatus.PLANNED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[2].id,
                    name="Svařování sestavy", sequence=3,
                    description="Svařování potrubní trasy DN200, WPS-03",
                    duration_hours=Decimal("80.0"), responsible="Petr Svoboda",
                    planned_start=now + timedelta(days=10),
                    planned_end=now + timedelta(days=20),
                    status=OperationStatus.PLANNED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[2].id,
                    name="Tlaková zkouška", sequence=4,
                    description="Hydrostatická tlaková zkouška 1.5x PN dle EN 13480-5",
                    duration_hours=Decimal("8.0"), responsible="Petr Svoboda",
                    planned_start=now + timedelta(days=21),
                    planned_end=now + timedelta(days=22),
                    status=OperationStatus.PLANNED.value,
                ),
                # ZAK-2026-008 (VYROBA) — 5 operací
                Operation(
                    id=uuid4(), order_id=orders[7].id,
                    name="Řezání a příprava polotovarů", sequence=1,
                    description="Dělení trubek DN300 P265GH, frézování úkosů",
                    duration_hours=Decimal("12.0"), responsible="Petr Svoboda",
                    planned_start=now - timedelta(days=8),
                    planned_end=now - timedelta(days=6),
                    actual_start=now - timedelta(days=8),
                    actual_end=now - timedelta(days=6),
                    status=OperationStatus.COMPLETED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[7].id,
                    name="Svařování T-kusů", sequence=2,
                    description="Svařování T-kusů DN300 PN25 dle WPS-02",
                    duration_hours=Decimal("48.0"), responsible="Petr Svoboda",
                    planned_start=now - timedelta(days=6),
                    planned_end=now + timedelta(days=1),
                    actual_start=now - timedelta(days=6),
                    status=OperationStatus.IN_PROGRESS.value,
                    notes="Svařování probíhá, hotovo 8 z 12 kusů",
                ),
                Operation(
                    id=uuid4(), order_id=orders[7].id,
                    name="CNC obrábění hrdel", sequence=3,
                    description="CNC obrábění přírubových hrdel (kooperace CNC Frýdek)",
                    duration_hours=Decimal("24.0"), responsible="CNC Obrábění Frýdek",
                    planned_start=now + timedelta(days=2),
                    planned_end=now + timedelta(days=5),
                    status=OperationStatus.PLANNED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[7].id,
                    name="Tepelné zpracování", sequence=4,
                    description="Žíhání ke snížení pnutí (kooperace TZ Třinec)",
                    duration_hours=Decimal("16.0"), responsible="TZ Třinec",
                    planned_start=now + timedelta(days=7),
                    planned_end=now + timedelta(days=9),
                    status=OperationStatus.PLANNED.value,
                ),
                Operation(
                    id=uuid4(), order_id=orders[7].id,
                    name="NDT + výstupní kontrola", sequence=5,
                    description="UT kontrola svarů 100%, rozměrový protokol, balení",
                    duration_hours=Decimal("12.0"), responsible="Petr Svoboda",
                    planned_start=now + timedelta(days=10),
                    planned_end=now + timedelta(days=12),
                    status=OperationStatus.PLANNED.value,
                ),
            ]
            db.add_all(operations)
            await db.flush()
            print(f"  operations: seeded {len(operations)} items")

        # =====================================================================
        # 5. OFFERS (nabídky)
        # =====================================================================
        count = (await db.execute(select(func.count()).select_from(Offer))).scalar()
        if count and count > 0:
            print(f"  offers: already has {count} rows, skipping")
        else:
            offers = [
                Offer(
                    id=uuid4(), order_id=orders[0].id,
                    number="NAB-2026-001",
                    total_price=Decimal("368000.00"),
                    valid_until=today + timedelta(days=30),
                    status=OfferStatus.ACCEPTED,
                ),
                Offer(
                    id=uuid4(), order_id=orders[1].id,
                    number="NAB-2026-002",
                    total_price=Decimal("520000.00"),
                    valid_until=today + timedelta(days=14),
                    status=OfferStatus.SENT,
                ),
                Offer(
                    id=uuid4(), order_id=orders[2].id,
                    number="NAB-2026-003",
                    total_price=Decimal("907200.00"),
                    valid_until=today + timedelta(days=21),
                    status=OfferStatus.ACCEPTED,
                ),
                Offer(
                    id=uuid4(), order_id=orders[4].id,
                    number="NAB-2026-004",
                    total_price=Decimal("185000.00"),
                    valid_until=today + timedelta(days=30),
                    status=OfferStatus.DRAFT,
                ),
                Offer(
                    id=uuid4(), order_id=orders[7].id,
                    number="NAB-2026-005",
                    total_price=Decimal("306800.00"),
                    valid_until=today - timedelta(days=10),
                    status=OfferStatus.ACCEPTED,
                ),
            ]
            db.add_all(offers)
            await db.flush()
            print(f"  offers: seeded {len(offers)} items")

        # =====================================================================
        # 6. USER POINTS (gamifikace)
        # =====================================================================
        count = (await db.execute(select(func.count()).select_from(UserPoints))).scalar()
        if count and count > 0:
            print(f"  user_points: already has {count} rows, skipping")
        else:
            points = [
                # Obchodník — body za nabídky a zakázky
                UserPoints(
                    id=uuid4(), user_id=obchodnik.id,
                    action=PointsAction.ORDER_STATUS_CHANGE,
                    points=10, description="Zakázka ZAK-2026-001 → NABÍDKA",
                    entity_type="order", entity_id=orders[0].id,
                    earned_at=now - timedelta(days=20),
                ),
                UserPoints(
                    id=uuid4(), user_id=obchodnik.id,
                    action=PointsAction.ORDER_STATUS_CHANGE,
                    points=10, description="Zakázka ZAK-2026-002 → NABÍDKA",
                    entity_type="order", entity_id=orders[1].id,
                    earned_at=now - timedelta(days=18),
                ),
                UserPoints(
                    id=uuid4(), user_id=obchodnik.id,
                    action=PointsAction.ORDER_STATUS_CHANGE,
                    points=20, description="Zakázka ZAK-2026-001 → OBJEDNÁVKA",
                    entity_type="order", entity_id=orders[0].id,
                    earned_at=now - timedelta(days=15),
                ),
                UserPoints(
                    id=uuid4(), user_id=obchodnik.id,
                    action=PointsAction.ORDER_COMPLETE,
                    points=50, description="Zakázka ZAK-2026-007 → DOKONČENO",
                    entity_type="order", entity_id=orders[6].id,
                    earned_at=now - timedelta(days=5),
                ),
                # Technolog — body za kalkulace a dokumenty
                UserPoints(
                    id=uuid4(), user_id=technolog.id,
                    action=PointsAction.CALCULATION_COMPLETE,
                    points=25, description="Kalkulace ZAK-2026-001 schválena",
                    entity_type="calculation", entity_id=None,
                    earned_at=now - timedelta(days=14),
                ),
                UserPoints(
                    id=uuid4(), user_id=technolog.id,
                    action=PointsAction.CALCULATION_COMPLETE,
                    points=25, description="Kalkulace ZAK-2026-008 nabídnuta",
                    entity_type="calculation", entity_id=None,
                    earned_at=now - timedelta(days=7),
                ),
                UserPoints(
                    id=uuid4(), user_id=technolog.id,
                    action=PointsAction.DOCUMENT_UPLOAD,
                    points=5, description="Nahrán výrobní výkres ZAK-2026-001",
                    entity_type="document", entity_id=None,
                    earned_at=now - timedelta(days=12),
                ),
                UserPoints(
                    id=uuid4(), user_id=technolog.id,
                    action=PointsAction.DOCUMENT_UPLOAD,
                    points=5, description="Nahrán WPS pro P265GH",
                    entity_type="document", entity_id=None,
                    earned_at=now - timedelta(days=11),
                ),
                UserPoints(
                    id=uuid4(), user_id=technolog.id,
                    action=PointsAction.ORDER_STATUS_CHANGE,
                    points=15, description="Zakázka ZAK-2026-001 → VÝROBA",
                    entity_type="order", entity_id=orders[0].id,
                    earned_at=now - timedelta(days=10),
                ),
                # Admin — body za dokončení
                UserPoints(
                    id=uuid4(), user_id=admin.id,
                    action=PointsAction.ORDER_STATUS_CHANGE,
                    points=20, description="Zakázka ZAK-2026-006 → FAKTURACE",
                    entity_type="order", entity_id=orders[5].id,
                    earned_at=now - timedelta(days=8),
                ),
                UserPoints(
                    id=uuid4(), user_id=admin.id,
                    action=PointsAction.ORDER_STATUS_CHANGE,
                    points=15, description="Zakázka ZAK-2026-004 → EXPEDICE",
                    entity_type="order", entity_id=orders[3].id,
                    earned_at=now - timedelta(days=3),
                ),
                # Vedení — body za review
                UserPoints(
                    id=uuid4(), user_id=vedeni.id,
                    action=PointsAction.CALCULATION_COMPLETE,
                    points=25, description="Schválení kalkulace ZAK-2026-001",
                    entity_type="calculation", entity_id=None,
                    earned_at=now - timedelta(days=14),
                ),
            ]
            db.add_all(points)
            await db.flush()
            print(f"  user_points: seeded {len(points)} items")

        # =====================================================================
        # 7. NOTIFICATIONS (notifikace)
        # =====================================================================
        count = (await db.execute(select(func.count()).select_from(Notification))).scalar()
        if count and count > 0:
            print(f"  notifications: already has {count} rows, skipping")
        else:
            notifications = [
                Notification(
                    id=uuid4(), user_id=admin.id,
                    type=NotificationType.EMAIL_NEW,
                    title="Nový email",
                    message="Poptávka od ŠKODA AUTO — kolena DN150 PN16",
                    link="/inbox", read=True,
                ),
                Notification(
                    id=uuid4(), user_id=admin.id,
                    type=NotificationType.EMAIL_CLASSIFIED,
                    title="Email klasifikován",
                    message="Email od ŠKODA AUTO klasifikován jako POPTÁVKA (94%)",
                    link="/inbox", read=True,
                ),
                Notification(
                    id=uuid4(), user_id=admin.id,
                    type=NotificationType.ORDER_STATUS_CHANGED,
                    title="Změna stavu zakázky",
                    message="ZAK-2026-001 přesunuta do VÝROBA",
                    link="/zakazky", read=True,
                ),
                Notification(
                    id=uuid4(), user_id=obchodnik.id,
                    type=NotificationType.CALCULATION_COMPLETE,
                    title="Kalkulace dokončena",
                    message="Kalkulace ZAK-2026-008 připravena k nabídce",
                    link="/kalkulace", read=False,
                ),
                Notification(
                    id=uuid4(), user_id=technolog.id,
                    type=NotificationType.ORDER_STATUS_CHANGED,
                    title="Nová zakázka ve výrobě",
                    message="ZAK-2026-008 (T-kusy DN300) přesunuta do VÝROBA",
                    link="/zakazky", read=False,
                ),
                Notification(
                    id=uuid4(), user_id=admin.id,
                    type=NotificationType.EMAIL_NEW,
                    title="Reklamace",
                    message="Reklamace od Siemens — potrubní oblouk ZAK-2025-089",
                    link="/inbox", read=False,
                ),
                Notification(
                    id=uuid4(), user_id=vedeni.id,
                    type=NotificationType.POHODA_SYNC_COMPLETE,
                    title="Synchronizace s Pohodou",
                    message="Sync dokončen: 12 záznamů synchronizováno",
                    link="/pohoda", read=True,
                ),
                Notification(
                    id=uuid4(), user_id=admin.id,
                    type=NotificationType.DOCUMENT_UPLOADED,
                    title="Nový dokument",
                    message="Materiálový atest 3.1 nahrán k ZAK-2026-001",
                    link="/dokumenty", read=False,
                ),
            ]
            db.add_all(notifications)
            await db.flush()
            print(f"  notifications: seeded {len(notifications)} items")

        # =====================================================================
        # 8. UPDATE CUSTOMER CATEGORIES (doplnění A/B/C kategorií)
        # =====================================================================
        updates = [
            ("ŠKODA AUTO a.s.", "A", Decimal("5.00"), 30, Decimal("5000000")),
            ("ČEZ, a.s.", "A", Decimal("3.00"), 45, Decimal("10000000")),
            ("Siemens, s.r.o.", "A", Decimal("4.00"), 30, Decimal("3000000")),
            ("Teplárna Liberec, a.s.", "B", Decimal("2.00"), 14, Decimal("1000000")),
            ("ARMATURY Group a.s.", "B", Decimal("1.50"), 14, Decimal("500000")),
        ]
        for company_name, category, discount, terms, limit in updates:
            result = await db.execute(
                select(Customer).where(Customer.company_name == company_name)
            )
            cust = result.scalar_one_or_none()
            if cust:
                cust.category = category
                cust.discount_percent = discount
                cust.payment_terms_days = terms
                cust.credit_limit = limit
        print("  customers: updated categories/discounts/credit limits")

        await db.commit()
        print("\nDone! All additional data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_additional())
