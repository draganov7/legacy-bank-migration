import duckdb


def main() -> None:
    connection = duckdb.connect(":memory:")
    result = connection.execute("SELECT 'bank migration project ready'").fetchone()
    connection.close()

    print(result[0])


if __name__ == "__main__":
    main()