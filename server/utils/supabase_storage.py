from supabase_client import supabase
import uuid
import mimetypes

def upload_to_supabase(file, bucket_name="arogya_sahayak", folder_name=""):
    """
    file: Django/Flask file object
    bucket_name: Supabase bucket name
    folder_name: optional folder inside bucket
    """
    file_ext = file.name.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"

    # Agar folder diya ho to path me add karo
    if folder_name:
        path = f"{folder_name}/{file_name}"
    else:
        path = file_name

    # Detect MIME type
    content_type, _ = mimetypes.guess_type(file.name)
    if not content_type:
        content_type = "application/octet-stream"

    # Read raw bytes
    file_bytes = file.read()

    # Upload to Supabase
    res = supabase.storage.from_(bucket_name).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type}
    )

    if res:
        public_url = supabase.storage.from_(bucket_name).get_public_url(path)
        return public_url
    return None
