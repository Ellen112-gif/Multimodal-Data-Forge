import json
import os
import urllib.request
import zipfile


NUM_IMAGES = 1000

DATA_DIR = "data/visual_genome"
IMAGE_DIR = os.path.join(DATA_DIR, "images")
OUTPUT_PATH = os.path.join(DATA_DIR, "samples.jsonl")

IMAGE_METADATA_URL = (
    "https://homes.cs.washington.edu/~ranjay/"
    "visualgenome/data/dataset/image_data.json.zip"
)

REGION_DESCRIPTION_URL = (
    "https://homes.cs.washington.edu/~ranjay/"
    "visualgenome/data/dataset/region_descriptions.json.zip"
)


def download_file(url, path):
    if os.path.exists(path):
        print(f"Exists: {path}")
        return

    print(f"Downloading: {url}")
    urllib.request.urlretrieve(url, path)


def load_json_from_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        json_file = zf.namelist()[0]

        with zf.open(json_file) as f:
            return json.load(f)


def download_image(url, path):
    if os.path.exists(path):
        return True

    try:
        urllib.request.urlretrieve(url, path)
        return True

    except Exception as e:
        print(f"Failed: {url} | {e}")
        return False


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

    metadata_zip = os.path.join(
        DATA_DIR,
        "image_data.json.zip"
    )

    regions_zip = os.path.join(
        DATA_DIR,
        "region_descriptions.json.zip"
    )

    download_file(
        IMAGE_METADATA_URL,
        metadata_zip
    )

    download_file(
        REGION_DESCRIPTION_URL,
        regions_zip
    )

    metadata = load_json_from_zip(metadata_zip)
    regions = load_json_from_zip(regions_zip)

    region_map = {
        item["id"]: item["regions"]
        for item in regions
    }

    samples = []

    for item in metadata:
        if len(samples) >= NUM_IMAGES:
            break

        image_id = item["image_id"]
        image_url = item["url"]

        image_path = os.path.join(
            IMAGE_DIR,
            f"vg_{image_id:06d}.jpg"
        )

        region_list = region_map.get(
            image_id,
            []
        )

        if not region_list:
            continue

        text = region_list[0].get(
            "phrase",
            ""
        ).strip()

        if not text:
            continue

        if not download_image(
            image_url,
            image_path
        ):
            continue

        samples.append({
            "source": "visual_genome",
            "image_id": image_id,
            "image_path": image_path,
            "image_url": image_url,
            "width": item.get("width"),
            "height": item.get("height"),
            "text": text,
        })

        if len(samples) % 100 == 0:
            print(
                f"Prepared: "
                f"{len(samples)}/{NUM_IMAGES}"
            )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        for sample in samples:
            f.write(
                json.dumps(
                    sample,
                    ensure_ascii=False
                ) + "\n"
            )

    print(
        f"\nDone: {len(samples)} samples"
    )

    print(
        f"Images: {IMAGE_DIR}"
    )

    print(
        f"Manifest: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()