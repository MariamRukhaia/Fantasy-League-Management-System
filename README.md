# MOTENTITY — Fantasy League Management System

A full-stack fantasy sports management platform built with **Python, Flask, MySQL, and SQLAlchemy**.

MOTENTITY allows users to create and participate in fantasy leagues, manage teams and players, propose trades, submit waiver requests, track matches, and manage their profiles through a database-driven web application.

The project focuses heavily on **relational database design, SQL programming, backend development, authentication, and transactional data management**.

---

## Features

### 🔐 User Authentication

- User registration and login
- BCrypt password hashing
- Session-based authentication
- Editable user profiles
- Commissioner and standard-user roles
- Role-based access to league functionality

### 🏆 League Management

Users can:

- View leagues they participate in
- Create new fantasy leagues
- Assign league commissioners
- Configure league type
- Set maximum team capacity
- Access teams within individual leagues

League creation is restricted based on user role.

### 👥 Team & Player Management

Users can:

- View teams within leagues
- Browse team rosters
- View player information
- Add available players to their team
- Remove players from their roster
- Manage players while a draft is active

### 🔄 Player Trading

The trading system allows users to:

1. Select a league
2. Select another team
3. Choose a player from their own team
4. Choose a player from the opposing team
5. Submit a proposed trade
6. Track proposed trades

Trade creation is integrated with the relational database through stored procedures and transaction handling.

### 📋 Waiver System

Users can submit players to the waiver system, while authorized league commissioners can review and approve waiver requests.

Waiver information tracks:

- Team
- Player
- Waiver status
- Pickup date
- League commissioner

### 🏟️ Match Tracking

Users can browse teams and search for match information.

Match records include:

- Participating teams
- Match date
- Final score
- Opponent
- Match history

---

## 🗄️ Database Design

MOTENTITY is built around a relational MySQL database modeling the relationships between fantasy sports users, leagues, teams, players, matches, trades, drafts, and waivers.

### Core Entities

```text
User
 │
 ├──────── owns ────────► Team
 │                         │
 │                         ├──── contains ────► Player
 │                         │
 │                         └──── belongs to ──► League
 │
 └──── commissions ─────► League
                           │
                           ├──── Draft
                           ├──── TeamMatch
                           ├──── Trade
                           └──── Waiver
```

The database contains entities for:

| Entity | Purpose |
|---|---|
| `User` | Stores account and profile information |
| `League` | Represents fantasy leagues and commissioners |
| `Team` | Stores fantasy teams, rankings, and points |
| `Player` | Stores player information and fantasy points |
| `Draft` | Tracks league draft information and status |
| `TeamMatch` | Stores scheduled/completed team matches |
| `PlayerStatistic` | Stores player performance data |
| `Trade` | Tracks proposed player trades |
| `Waiver` | Manages player waiver requests |
| `TeamToPlayer` | Implements the team-player relationship |

---

## ⚙️ Database Programming

The application combines SQLAlchemy with direct SQL to perform database operations.

### Stored Procedures

Stored procedures are used for operations including:

```sql
CALL signUp(...)
CALL newLeague(...)
CALL newTrade(...)
CALL newWaiver(...)
```

This moves important database operations into reusable database-side logic.

### Relational Queries

The backend uses:

- `INNER JOIN`
- Subqueries
- `UNION`
- Parameterized SQL
- Multi-table queries
- Search queries
- Insert, update, and delete operations

### Transaction Management

Operations that modify related data use explicit database transactions with:

```python
transaction.commit()
transaction.rollback()
```

This helps prevent partially completed operations when an error occurs.

---

## 🛠️ Tech Stack

### Backend

`Python` · `Flask` · `SQLAlchemy` · `Flask-SQLAlchemy`

### Database

`MySQL` · `PyMySQL` · `SQL`

### Security

`BCrypt` · `Flask Sessions`

### Frontend

`HTML5` · `CSS3` · `Jinja2`

---

## 🔒 Security

The application incorporates:

- BCrypt password hashing
- Parameterized SQL queries
- Session-based authentication
- Role-based functionality
- Environment-based database credentials
- Database transaction rollback on failed operations

Sensitive configuration such as database passwords and Flask secret keys is excluded from version control.

---


## 👥 Authors

**Mariam Rukhaia**  
**Elsa Mitchell**  
**Tinos Vafias**  
**Oleg Vengrovych**
