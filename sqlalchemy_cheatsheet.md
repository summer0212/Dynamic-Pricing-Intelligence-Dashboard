# 📋 SQLAlchemy ORM → SQL Cheat Sheet

## READ Operations

| ORM (What you write) | SQL (What PostgreSQL executes) | Used Where |
|---|---|---|
| `db.query(User).all()` | `SELECT * FROM users` | — |
| `db.query(User).first()` | `SELECT * FROM users LIMIT 1` | — |
| `db.query(User).filter(User.email == "a@b.com").first()` | `SELECT * FROM users WHERE email='a@b.com' LIMIT 1` | auth.py — login |
| `db.query(Product).filter(Product.org_id == "xyz").all()` | `SELECT * FROM products WHERE org_id='xyz'` | products.py — multi-tenancy |
| `db.query(Product).filter(Product.id == "abc", Product.org_id == "xyz").first()` | `SELECT * FROM products WHERE id='abc' AND org_id='xyz' LIMIT 1` | products.py — get single product |
| `db.query(Organization).filter(Organization.invite_code == "TECH2026").first()` | `SELECT * FROM organizations WHERE invite_code='TECH2026' LIMIT 1` | auth.py — join org |

## CREATE Operations

| ORM | SQL | Used Where |
|---|---|---|
| `user = User(email="a@b.com", name="Alisha")` | Nothing yet — just a Python object in memory | auth.py — signup |
| `db.add(user)` | Nothing yet — queued for saving | auth.py — signup |
| `db.flush()` | `INSERT INTO users (...) VALUES (...)` — sends to DB but NOT permanent | auth.py — need org.id before creating user |
| `db.commit()` | `COMMIT` — makes ALL pending changes permanent | auth.py — after all records created |
| `db.add_all([user1, user2])` | Queues multiple inserts at once | seed_data.py |

## UPDATE Operations

| ORM | SQL | Used Where |
|---|---|---|
| `product.current_price = 21240` then `db.commit()` | `UPDATE products SET current_price=21240 WHERE id='abc'` | products.py — update |
| `setattr(product, "current_price", 21240)` | Same as above — dynamic version | products.py — partial update |

## DELETE Operations

| ORM | SQL | Used Where |
|---|---|---|
| `db.delete(product)` then `db.commit()` | `DELETE FROM products WHERE id='abc'` | products.py — delete |

## Session Lifecycle

| ORM | What it does | Analogy |
|---|---|---|
| `SessionLocal()` | Opens a new database connection | Grab a shopping cart |
| `db.add(obj)` | Queue object for saving | Put item in cart |
| `db.flush()` | Send to DB but DON'T finalize (can still undo) | Items scanned but not paid |
| `db.commit()` | Finalize ALL changes permanently | Pay at checkout ✅ |
| `db.rollback()` | Undo ALL uncommitted changes | Empty the cart, put everything back |
| `db.refresh(obj)` | Reload object from DB (get auto-generated fields like id, created_at) | Check receipt for final total |
| `db.close()` | Return connection to pool | Return the cart |

## Filter Operators

| ORM | SQL | Meaning |
|---|---|---|
| `User.email == "a@b.com"` | `WHERE email = 'a@b.com'` | Exact match |
| `User.email != "a@b.com"` | `WHERE email != 'a@b.com'` | Not equal |
| `Product.current_price > 1000` | `WHERE current_price > 1000` | Greater than |
| `Product.category.in_(["electronics", "apparel"])` | `WHERE category IN ('electronics', 'apparel')` | In list |
| `Product.name.like("%Sony%")` | `WHERE name LIKE '%Sony%'` | Pattern match |
| `Product.name.ilike("%sony%")` | `WHERE name ILIKE '%sony%'` | Case-insensitive match |

## Key Differences: flush() vs commit()

```
db.add(org)
db.flush()     ← SQL runs, org gets an ID, but it's like a "preview"
               ← If something fails later → everything is UNDONE

db.add(user)   ← user uses org.id (which we got from flush)
db.commit()    ← NOW both org and user are saved permanently
               ← This is a TRANSACTION — all or nothing
```

**Why not just commit twice?**
```
db.add(org)
db.commit()    ← org is saved permanently
db.add(user)   ← user uses org.id
# If THIS CRASHES → org exists but user doesn't → ORPHAN DATA! 🚨

# With flush + single commit → if user creation fails, org is also undone ✅
```
