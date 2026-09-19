import csv
import threading
import time

from tqdm import tqdm
from gmail_cleaner.gmail_api import get_gmail_service

def execute_with_retry(request, max_retries=10):
    from googleapiclient.errors import HttpError

    for attempt in range(max_retries):
        try:
            return request.execute()

        except HttpError as error:
            if error.resp.status != 403:
                raise

            wait_seconds = min(
                5 * (2 ** attempt),
                60,
            )

            for remaining in range(
                wait_seconds,
                0,
                -1,
            ):
                print(
                    f"\rCuota Gmail alcanzada. "
                    f"Reintentando en {remaining:2d}s...",
                    end="",
                    flush=True,
                )

                time.sleep(1)

            print(
                "\r" + " " * 60 + "\r",
                end="",
                flush=True,
            )

        except TimeoutError:
            wait_seconds = min(
                5 * (2 ** attempt),
                60,
            )

            for remaining in range(
                wait_seconds,
                0,
                -1,
            ):
                print(
                    f"\rTimeout de Gmail. "
                    f"Reintentando en {remaining:2d}s...",
                    end="",
                    flush=True,
                )

                time.sleep(1)

            print(
                "\r" + " " * 60 + "\r",
                end="",
                flush=True,
            )

    raise RuntimeError(
        "Se agotaron los reintentos al comunicarse con Gmail."
    )

def get_message_metadata(service, message_id):
    message = execute_with_retry(
        (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
                metadataHeaders=["From", "To", "Subject", "Date"],
            )
        )
    )

    headers = {
        header["name"].lower(): header["value"]
        for header in message.get("payload", {}).get("headers", [])
    }

    def find_attachments(parts):
        attachments = []

        for part in parts or []:
            filename = part.get("filename", "")
            body = part.get("body", {})

            if filename or body.get("attachmentId"):
                attachments.append(
                    filename or "[adjunto sin nombre]"
                )

            attachments.extend(
                find_attachments(part.get("parts", []))
            )

        return attachments

    attachments = find_attachments(
        message.get("payload", {}).get("parts", [])
    )

    return {
        "id": message["id"],
        "thread_id": message["threadId"],
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "labels": message.get("labelIds", []),
        "snippet": message.get("snippet", ""),
        "size": message.get("sizeEstimate", 0),
        "has_attachments": bool(attachments),
        "attachment_count": len(attachments),
    }


class RateLimiter:
    def __init__(self, requests_per_minute):
        self.interval = 60 / requests_per_minute
        self.lock = threading.Lock()
        self.next_request = time.monotonic()

    def wait(self):
        with self.lock:
            now = time.monotonic()

            if now < self.next_request:
                time.sleep(self.next_request - now)

            self.next_request = max(
                self.next_request,
                time.monotonic(),
            ) + self.interval

def get_all_messages_metadata(
    service,
    max_messages=100,
    output_file=None,
    processed_ids=None,
):

    messages = []
    processed_ids = (
        processed_ids
        if processed_ids is not None
        else set()
    )

    page_token = None
    rate_limiter = RateLimiter(100)

    is_resume = bool(processed_ids)

    progress = tqdm(
        total=max_messages,
        desc="Inventario Gmail",
        unit="msg",
    )

    scan_progress = None

    if is_resume:
        scan_progress = tqdm(
            total=None,
            desc="Revisando Gmail",
            unit="msg",
        )

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

    csvfile = None
    writer = None

    if output_file:
        csvfile = open(
            output_file,
            "a" if processed_ids else "w",
            newline="",
            encoding="utf-8",
        )

        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames,
        )

        if not processed_ids:
            writer.writeheader()

    try:
        while max_messages is None or len(messages) < max_messages:

            rate_limiter.wait()

            response = execute_with_retry(
                (
                    service.users()
                    .messages()
                    .list(
                        userId="me",
                        maxResults=100,
                        pageToken=page_token,
                    )
                )
            )

            page_messages = response.get("messages", [])

            if scan_progress is not None:
                scan_progress.update(len(page_messages))

            message_ids = [
                message
                for message in page_messages
                if message["id"] not in processed_ids
            ]

            skipped = len(page_messages) - len(message_ids)

            if scan_progress is not None:
                scan_progress.set_postfix(
                    nuevos=len(messages),
                    saltados=skipped,
                )

            if not message_ids:
                page_token = response.get("nextPageToken")

                if not page_token:
                    print("\nNo quedan mensajes nuevos por procesar.")
                    break

                continue

            if max_messages is not None:
                remaining = max_messages - len(messages)
                message_ids = message_ids[:remaining]

            for message_id in message_ids:
                rate_limiter.wait()

                message = get_message_metadata(
                    service,
                    message_id["id"],
                )

                messages.append(message)
                processed_ids.add(message["id"])

                if writer:
                    row = message.copy()
                    row["labels"] = ",".join(row["labels"])

                    writer.writerow(row)
                    csvfile.flush()

                progress.update(1)

                if scan_progress is not None:
                    scan_progress.set_postfix(
                        nuevos=len(messages),
                        saltados=skipped,
                    )

                if max_messages is not None and len(messages) >= max_messages:
                    break

            page_token = response.get("nextPageToken")

            if not page_token:
                break

    finally:
        progress.close()

        if scan_progress is not None:
            scan_progress.close()

        if csvfile:
            csvfile.close()

    return messages
