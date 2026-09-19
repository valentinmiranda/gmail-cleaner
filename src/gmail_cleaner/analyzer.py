import csv
from collections import Counter
from pathlib import Path
from email.utils import parseaddr


def load_inventory(path):
    path = Path(path)

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csvfile:
        return list(csv.DictReader(csvfile))


def analyze_inventory(
    path,
    sender_filter=None,
    domain_filter=None,
    list_messages=False,
    limit=None,
    sort_by=None,
    export_path=None,
):
    messages = load_inventory(path)

    if sender_filter:
        sender_filters = [
            sender.strip().lower()
            for sender in sender_filter.split(",")
            if sender.strip()
        ]

        messages = [
            message
            for message in messages
            if any(
                sender_filter in message.get("from", "").lower()
                for sender_filter in sender_filters
            )
        ]

    if domain_filter:
        domain_filter = domain_filter.lower().strip()

        messages = [
            message
            for message in messages
            if "@" in message.get("from", "")
            and parseaddr(message.get("from", ""))[1]
            .lower()
            .endswith("@" + domain_filter)
        ]

    if sort_by == "size":
        messages = sorted(
            messages,
            key=lambda message: int(
                message.get("size") or 0
            ),
            reverse=True,
        )

    elif sort_by == "date":
        messages = sorted(
            messages,
            key=lambda message: message.get("date", ""),
            reverse=True,
        )

    if limit is not None:
        messages = messages[:limit]

    if export_path:
        export_file = Path(export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "id",
            "thread_id",
            "from",
            "to",
            "subject",
            "date",
            "labels",
            "snippet",
            "size",
            "has_attachments",
            "attachment_count",
        ]

        with export_file.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for message in messages:
                writer.writerow(message)

        print(f"\nExportados: {len(messages)} mensajes")
        print(f"Archivo: {export_file}")

    if list_messages:
        print(f"\nMensajes: {len(messages)}")

        for message in messages:
            size_mb = int(
                message.get("size") or 0
            ) / 1024 / 1024

            print(
                f"{message.get('id', '')}  "
                f"{message.get('date', '')}  "
                f"{size_mb:7.2f} MB  "
                f"{message.get('from', '')}  "
                f"{message.get('subject', '')}"
            )

        return


    senders = Counter()
    sender_sizes = Counter()
    sender_with_attachments = Counter()
    sender_attachment_count = Counter()

    domains = Counter()
    domain_with_attachments = Counter()
    domain_attachment_count = Counter()

    sizes = []

    for message in messages:
        sender = message.get("from", "")

        _, email_address = parseaddr(sender)
        email_address = email_address.lower()

        size = int(message.get("size") or 0)
        sizes.append(size)

        has_attachments = (
            message.get("has_attachments", "").lower()
            == "true"
        )

        attachment_count = int(
            message.get("attachment_count") or 0
        )

        if email_address:
            senders[email_address] += 1
            sender_sizes[email_address] += size

            if has_attachments:
                sender_with_attachments[email_address] += 1

            sender_attachment_count[email_address] += (
                attachment_count
            )

            if "@" in email_address:
                domain = email_address.split("@", 1)[1]

                domains[domain] += 1

                if has_attachments:
                    domain_with_attachments[domain] += 1

                domain_attachment_count[domain] += (
                    attachment_count
                )

    print(f"Mensajes analizados: {len(messages)}")

    total_size = sum(sizes)

    print("\nTop remitentes:")
    for sender, count in senders.most_common(20):
        size_mb = sender_sizes[sender] / 1024 / 1024

        percentage = (
            sender_sizes[sender] / total_size * 100
            if total_size
            else 0
        )

        print(
            f"{count:5}  "
            f"{size_mb:8.2f} MB  "
            f"{percentage:5.1f}%  "
            f"{sender}"
        )

    print("\nTop dominios:")
    for domain, count in domains.most_common(20):
        print(f"{count:5}  {domain}")

    print("\nEstadísticas de adjuntos por remitente:")

    for sender, count in senders.most_common(20):
        with_attachments = sender_with_attachments[sender]
        without_attachments = count - with_attachments
        attachment_count = sender_attachment_count[sender]

        print(
            f"{count:5} mensajes  "
            f"{with_attachments:5} con adjuntos  "
            f"{without_attachments:5} sin adjuntos  "
            f"{attachment_count:5} adjuntos  "
            f"{sender}"
        )

    print("\nEstadísticas de adjuntos por dominio:")

    for domain, count in domains.most_common(20):
        with_attachments = domain_with_attachments[domain]
        without_attachments = count - with_attachments
        attachment_count = domain_attachment_count[domain]

        print(
            f"{count:5} mensajes  "
            f"{with_attachments:5} con adjuntos  "
            f"{without_attachments:5} sin adjuntos  "
            f"{attachment_count:5} adjuntos  "
            f"{domain}"
        )

    total_with_attachments = sum(
        sender_with_attachments.values()
    )

    total_attachments = sum(
        sender_attachment_count.values()
    )

    print("\nResumen de adjuntos:")
    print(
        f"Mensajes con adjuntos: "
        f"{total_with_attachments}"
    )
    print(
        f"Mensajes sin adjuntos: "
        f"{len(messages) - total_with_attachments}"
    )
    print(
        f"Adjuntos detectados: "
        f"{total_attachments}"
    )

    print("\nTamaño total:")
    print(f"{total_size / 1024 / 1024:.2f} MB")

    print("\nCorreos más grandes:")
    largest = sorted(
        messages,
        key=lambda message: int(
            message.get("size") or 0
        ),
        reverse=True,
    )

    for message in largest[:20]:
        size_mb = int(
            message.get("size") or 0
        ) / 1024 / 1024

        print(
            f"{size_mb:8.2f} MB  "
            f"{message.get('from', '')}  "
            f"{message.get('subject', '')}"
        )
