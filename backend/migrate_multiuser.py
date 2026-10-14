"""T16: 다중 사용자·팀 테이블을 추가하고 기존 tasks 테이블에 열을 더한다.

- 없는 테이블(users, sessions, teams, team_members)만 만든다.
- tasks에 owner_id, visibility, team_id 열과 외래키·CHECK 제약을 추가한다. 이미 있으면 건너뛴다.
- 기존 행은 삭제하거나 바꾸지 않는다(owner_id NULL, visibility PRIVATE로 남는다).
- 실행 전 mysqldump로 백업한다. 여러 번 실행해도 결과가 같다.

실행: python -m backend.migrate_multiuser
"""

from sqlalchemy import inspect, text

from .database import Base, engine
from .models import TASK_TEAM_CHECK, TaskRow

NEW_TABLES = ("users", "sessions", "teams", "team_members")

# tasks에 추가할 정의. 순서대로 적용한다(외래키는 열이 있어야 만들 수 있다).
TASK_COLUMNS = {
    "owner_id": "ADD COLUMN owner_id INT NULL",
    "visibility": "ADD COLUMN visibility ENUM('PRIVATE','TEAM') NOT NULL DEFAULT 'PRIVATE'",
    "team_id": "ADD COLUMN team_id INT NULL",
}
TASK_FOREIGN_KEYS = {
    "fk_tasks_owner": "ADD CONSTRAINT fk_tasks_owner FOREIGN KEY (owner_id) REFERENCES users (id)",
    "fk_tasks_team": "ADD CONSTRAINT fk_tasks_team FOREIGN KEY (team_id) REFERENCES teams (id)",
}
TASK_CHECK = ("ck_tasks_team", f"ADD CONSTRAINT ck_tasks_team CHECK ({TASK_TEAM_CHECK})")


def check_constraint_names(connection) -> set[str]:
    rows = connection.execute(
        text(
            "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tasks' AND CONSTRAINT_TYPE = 'CHECK'"
        )
    )
    return {row[0] for row in rows}


def main() -> None:
    table = TaskRow.__tablename__
    inspector = inspect(engine)
    if not inspector.has_table(table):
        raise SystemExit("tasks 테이블이 없습니다. 새로 설치하는 경우 python -m backend.init_db를 실행하세요.")

    existing_tables = set(inspector.get_table_names())
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[name] for name in NEW_TABLES])
    for name in NEW_TABLES:
        print(f"{name}: {'이미 있음(변경 안 함)' if name in existing_tables else '만들었음'}")

    with engine.begin() as connection:
        before = connection.execute(text("SELECT COUNT(*) FROM tasks")).scalar_one()
        columns = {column["name"] for column in inspect(connection).get_columns(table)}
        foreign_keys = {fk["name"] for fk in inspect(connection).get_foreign_keys(table)}
        checks = check_constraint_names(connection)

        changes = [ddl for name, ddl in TASK_COLUMNS.items() if name not in columns]
        changes += [ddl for name, ddl in TASK_FOREIGN_KEYS.items() if name not in foreign_keys]
        if TASK_CHECK[0] not in checks:
            changes.append(TASK_CHECK[1])

        if changes:
            # 한 번의 ALTER로 적용한다. MariaDB DDL은 트랜잭션으로 되돌릴 수 없으므로 실행 전 백업이 필요하다.
            connection.execute(text(f"ALTER TABLE tasks {', '.join(changes)}"))
            print(f"tasks: {len(changes)}개 변경 적용")
            for ddl in changes:
                print(f"  - {ddl}")
        else:
            print("tasks: 이미 적용됨(변경 안 함)")

        after = connection.execute(text("SELECT COUNT(*) FROM tasks")).scalar_one()
        print(f"tasks 행 수: {before} → {after}")


if __name__ == "__main__":
    main()
