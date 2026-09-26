"""Idempotent Shanghai catalog bootstrap. Optional --admin-email grants the first operator roles."""

import argparse
import asyncio
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from . import models as m
from .db import SessionFactory, engine
from .security import digest, encrypt, normalize_email, now

SHANGHAI_ID = str(uuid5(NAMESPACE_URL, "marcus:city:shanghai"))
DISTRICTS = [
    ("huangpu", "黄浦区"),
    ("xuhui", "徐汇区"),
    ("changning", "长宁区"),
    ("jingan", "静安区"),
    ("putuo", "普陀区"),
    ("hongkou", "虹口区"),
    ("yangpu", "杨浦区"),
    ("minhang", "闵行区"),
    ("baoshan", "宝山区"),
    ("jiading", "嘉定区"),
    ("pudong", "浦东新区"),
    ("jinshan", "金山区"),
    ("songjiang", "松江区"),
    ("qingpu", "青浦区"),
    ("fengxian", "奉贤区"),
    ("chongming", "崇明区"),
]


async def seed(admin_email=None):
    async with SessionFactory.begin() as db:
        city = await db.get(m.City, SHANGHAI_ID)
        if not city:
            db.add(
                m.City(
                    id=SHANGHAI_ID,
                    code="shanghai",
                    name="上海",
                    country_code="CN",
                    timezone="Asia/Shanghai",
                    enabled=True,
                )
            )
            await db.flush()
        for code, name in DISTRICTS:
            id = str(uuid5(NAMESPACE_URL, "marcus:district:shanghai:" + code))
            if not await db.get(m.District, id):
                db.add(m.District(id=id, city_id=SHANGHAI_ID, code=code, name=name))
        if admin_email:
            from email_validator import validate_email

            email = normalize_email(validate_email(admin_email, check_deliverability=False).normalized)
            lookup = digest("email:" + email)
            u = await db.scalar(select(m.User).where(m.User.email_lookup_hash == lookup))
            if not u:
                # Bootstrap is an explicit trusted deployment operation, never an HTTP registration bypass.
                u = m.User(
                    email_lookup_hash=lookup,
                    email_ciphertext=encrypt(email),
                    email_verified_at=now(),
                    display_name="Marcus 编辑部",
                    terms_version="bootstrap",
                    terms_accepted_at=now(),
                    city_id=SHANGHAI_ID,
                )
                db.add(u)
                await db.flush()
            for role in ["admin", "editor", "moderator"]:
                if not await db.get(m.UserRole, (u.id, role)):
                    db.add(m.UserRole(user_id=u.id, role=role, granted_by=None))
    return SHANGHAI_ID


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email")
    args = parser.parse_args()
    print("Shanghai city id:", await seed(args.admin_email))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
