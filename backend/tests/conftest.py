import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# app.config instancia Settings() al importarse (lee DATABASE_URL/SUPABASE_URL
# del entorno); estos tests no tocan la base, así que alcanza con valores
# dummy para que el import no explote si no están seteados de verdad.
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
