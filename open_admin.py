import webbrowser
from pathlib import Path

def main():
    admin_path = Path(__file__).resolve().parent / "admin.html"
    print(f"Abriendo panel de administración en el navegador: {admin_path}")
    webbrowser.open(admin_path.as_uri())

if __name__ == "__main__":
    main()
