import argparse
import csv

from pathlib import Path
from gmail_cleaner.cleaner import dry_run, move_to_trash
from gmail_cleaner.gmail_api import get_gmail_service
from gmail_cleaner.inventory import get_all_messages_metadata
from gmail_cleaner.analyzer import analyze_inventory

def load_processed_ids(output_path):
    if not output_path.exists():
        return set()

    with output_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csvfile:
        reader = csv.DictReader(csvfile)

        return {
            row["id"]
            for row in reader
            if row.get("id")
        }


def save_to_csv():
    parser = argparse.ArgumentParser(
        description="Genera un inventario de mensajes de Gmail en CSV."
    )

    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=100,
        help="Número de mensajes a procesar.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="data/inventory.csv",
        help="Archivo CSV de salida.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe el archivo de salida si ya existe.",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanuda un inventario existente sin volver a procesar mensajes.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Inventaría todos los mensajes del buzón.",
    )

    args = parser.parse_args()

    output_path = Path(args.output)

    if output_path.exists() and not args.force and not args.resume:
        print(f"ERROR: El archivo ya existe: {output_path}")
        print("Usa --force para sobrescribirlo o --resume para continuar.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed_ids = set()

    if args.resume:
        processed_ids = load_processed_ids(output_path)
        print(f"Mensajes ya procesados: {len(processed_ids)}")

    service = get_gmail_service()

    if args.all:
        count = None

        print("Modo: inventario completo")
        print(f"Mensajes ya procesados: {len(processed_ids)}")

        if args.resume:
            print("Se omitirán los mensajes ya presentes en el CSV.")
    else:
        count = args.count

    if count is None:
        print("Procesando todos los mensajes nuevos...")
    else:
        print(f"Procesando hasta {count} mensajes nuevos...")
    print(f"Salida: {output_path}")

    messages = get_all_messages_metadata(
        service,
        max_messages=count,
        output_file=str(output_path),
        processed_ids=processed_ids,
    )

    processed_ids.update(message["id"] for message in messages)

    print(f"Nuevos mensajes guardados: {len(messages)}")
    print(f"Total procesados: {len(processed_ids)}")

def clean_inventory_cli():
    parser = argparse.ArgumentParser(
        description="Procesa mensajes seleccionados para limpieza."
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="data/to_delete.csv",
        help="CSV con los mensajes seleccionados.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué mensajes se procesarían sin modificar Gmail.",
    )

    parser.add_argument(
        "--delete",
        action="store_true",
        help="Envía los mensajes seleccionados a la papelera.",
    )

    args = parser.parse_args()

    if args.dry_run == args.delete:
        parser.error(
            "Debes indicar exactamente uno de: "
            "--dry-run o --delete."
        )

    if args.dry_run:
        dry_run(args.input)
        return

    move_to_trash(args.input)


def analyze_inventory_cli():
    parser = argparse.ArgumentParser(
        description="Analiza un inventario de Gmail."
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="data/inventory.csv",
        help="Archivo CSV del inventario.",
    )

    parser.add_argument(
        "--sender",
        help="Filtra por uno o varios remitentes separados por comas.",
    )

    parser.add_argument(
        "--domain",
        help="Filtra los mensajes por dominio del remitente.",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="Muestra los mensajes del inventario filtrado.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limita el número de mensajes mostrados.",
    )

    parser.add_argument(
        "--sort",
        choices=["date", "size"],
        help="Ordena los mensajes por fecha o tamaño.",
    )

    parser.add_argument(
        "--export",
        help="Exporta los mensajes filtrados a un CSV.",
    )

    args = parser.parse_args()

    analyze_inventory(
        args.input,
        sender_filter=args.sender,
        domain_filter=args.domain,
        list_messages=args.list,
        limit=args.limit,
        sort_by=args.sort,
        export_path=args.export,
    )


if __name__ == "__main__":
    save_to_csv()
