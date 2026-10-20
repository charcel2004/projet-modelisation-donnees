"""
Diagnostic d'installation PySpark — module PMD (M1), à exécuter avant le jour 5.

    python src/check_pyspark.py

Le script ne modifie rien. Il contrôle les cinq points qui font échouer une
installation, dans l'ordre où ils échouent, et donne la commande exacte à taper
pour chacun. Aucune dépendance : il fonctionne même si PySpark n'est pas installé.

Le piège le plus fréquent n'est pas l'absence de PySpark, c'est la version de Java :
PySpark 3.5 ne démarre pas sur un JDK 21, et l'erreur est illisible.
"""

import os
import platform
import re
import shutil
import subprocess
import sys

# Compatibilité Java / PySpark, d'après la documentation officielle Spark.
# Clé : version majeure de Java. Valeur : versions de PySpark qui l'acceptent.
JAVA_SUPPORT = {
    8:  ("3.5", "pyspark==3.5.*"),
    11: ("3.5 ou 4.0", "pyspark==3.5.*"),
    17: ("3.5 ou 4.0", "pyspark==3.5.*"),
    21: ("4.0 uniquement", "pyspark==4.0.*"),
}

GREEN, RED, YELLOW, BOLD, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[0m"
if platform.system() == "Windows" and not os.environ.get("WT_SESSION"):
    GREEN = RED = YELLOW = BOLD = RESET = ""   # vieux terminal Windows : pas de couleur


def line(symbol, label, detail="", color=""):
    print(f"  {color}{symbol}{RESET} {label}" + (f"\n      {detail}" if detail else ""))


def ok(label, detail=""):
    line("OK  ", label, detail, GREEN)


def fail(label, detail=""):
    line("ECHEC", label, detail, RED)


def warn(label, detail=""):
    line("!   ", label, detail, YELLOW)


def java_major_version():
    """Renvoie (version_majeure, texte_brut) ou (None, raison)."""
    java = shutil.which("java")
    if java is None:
        return None, "la commande java est introuvable dans le PATH"
    try:
        result = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=20)
    except Exception as error:
        return None, f"java n'a pas pu être exécuté ({error})"

    output = (result.stderr or "") + (result.stdout or "")
    match = re.search(r'version "(\d+)(?:\.(\d+))?', output)
    if not match:
        return None, f"version illisible dans la sortie de java -version :\n      {output.strip()[:120]}"

    major, minor = int(match.group(1)), match.group(2)
    # Avant Java 9, la version s'écrivait 1.8 : la majeure utile est le second nombre.
    if major == 1 and minor:
        major = int(minor)
    # On retient la ligne qui porte reellement la version : la premiere ligne
    # peut etre un message d'environnement (JAVA_TOOL_OPTIONS, par exemple).
    version_line = next((l.strip() for l in output.splitlines() if "version" in l.lower()), "")
    return major, version_line[:100]


def main():
    print(f"\n{BOLD}Diagnostic PySpark — module PMD{RESET}")
    print("=" * 72)

    problems = []

    # --- 1. Python ---------------------------------------------------------
    print(f"\n{BOLD}1. Python{RESET}")
    version = sys.version_info
    if version >= (3, 9):
        ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        fail(f"Python {version.major}.{version.minor} trop ancien",
             "PySpark exige Python 3.9 ou plus.")
        problems.append("python")

    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        ok("environnement virtuel actif", sys.prefix)
    else:
        warn("vous n'êtes PAS dans un environnement virtuel",
             "Activez-le avant d'installer, sinon PySpark ira dans le Python système :\n"
             "      source .venv/bin/activate      (Windows : .venv\\Scripts\\activate)")

    # --- 2. Java -----------------------------------------------------------
    print(f"\n{BOLD}2. Java (le point qui fait échouer la plupart des installations){RESET}")
    major, detail = java_major_version()

    if major is None:
        fail("Java introuvable", detail)
        print("\n      Installer un JDK 17, qui convient à toutes les versions de PySpark :")
        print("        Windows  : winget install EclipseAdoptium.Temurin.17.JDK")
        print("        macOS    : brew install --cask temurin@17")
        print("        Linux    : sudo apt install openjdk-17-jdk")
        problems.append("java")
        recommended = "pyspark==3.5.*"
    else:
        ok(f"Java {major} détecté", detail)
        if major in JAVA_SUPPORT:
            supported, recommended = JAVA_SUPPORT[major]
            print(f"      Java {major} fonctionne avec PySpark {supported}.")
            if major == 21:
                warn("Java 21 n'accepte QUE PySpark 4.0",
                     "Avec PySpark 3.5 vous obtiendriez une erreur illisible du type\n"
                     "      'UnsupportedOperationException: getSubject is not supported'.\n"
                     "      Installez pyspark==4.0.* ou rétrogradez vers un JDK 17.")
        else:
            recommended = "pyspark==3.5.*"
            fail(f"Java {major} n'est pas une version supportée",
                 "Spark supporte Java 8, 11, 17 et 21. Installez un JDK 17.")
            problems.append("java")

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        ok("JAVA_HOME défini", java_home)
    else:
        warn("JAVA_HOME n'est pas défini",
             "Facultatif si java est dans le PATH, mais certaines installations Windows\n"
             "      en ont besoin. En cas d'échec au démarrage, définissez-le.")

    # --- 3. PySpark installé ? --------------------------------------------
    print(f"\n{BOLD}3. Paquet PySpark{RESET}")
    try:
        import pyspark
        installed = pyspark.__version__
        ok(f"pyspark {installed} installé", os.path.dirname(pyspark.__file__))

        if major in (21,) and installed.startswith("3."):
            fail("combinaison incompatible",
                 f"Java 21 avec PySpark {installed} : Spark ne démarrera pas.\n"
                 f"      Corriger avec :  pip install --upgrade 'pyspark==4.0.*'")
            problems.append("combinaison")
        elif major is not None and major < 17 and installed.startswith("4."):
            fail("combinaison incompatible",
                 f"PySpark 4.0 exige Java 17 ou 21, or Java {major} est installé.\n"
                 f"      Corriger avec :  pip install 'pyspark==3.5.*'")
            problems.append("combinaison")
    except ImportError:
        installed = None
        fail("pyspark n'est pas installé",
             f"Installer avec :  pip install '{recommended}'")
        problems.append("pyspark")

    # --- 4. Démarrage réel d'une session ----------------------------------
    print(f"\n{BOLD}4. Démarrage d'une session Spark{RESET}")
    if installed is None or "java" in problems or "combinaison" in problems:
        warn("test ignoré", "corrigez d'abord les points ci-dessus.")
    else:
        print("      (premier démarrage : comptez 10 à 30 secondes)")
        try:
            from pyspark.sql import SparkSession
            spark = (SparkSession.builder
                     .appName("PMD-diagnostic")
                     .master("local[1]")
                     .config("spark.ui.enabled", "false")
                     .config("spark.sql.shuffle.partitions", "2")
                     .getOrCreate())
            spark.sparkContext.setLogLevel("ERROR")

            n_rows = spark.range(1000).filter("id % 7 = 0").count()
            spark.stop()

            if n_rows == 143:
                ok("session démarrée et calcul vérifié",
                   f"Spark {installed} a compté {n_rows} multiples de 7 sous 1000.")
            else:
                fail("résultat inattendu", f"{n_rows} au lieu de 143.")
                problems.append("calcul")
        except Exception as error:
            message = str(error).splitlines()[0][:150]
            fail("la session n'a pas démarré", message)
            if "getSubject" in str(error) or "SecurityManager" in str(error):
                print(f"      {YELLOW}Signature typique de l'incompatibilité Java 21 / PySpark 3.5.{RESET}")
                print("      Corriger avec :  pip install --upgrade 'pyspark==4.0.*'")
            elif "JAVA_HOME" in str(error) or "java" in str(error).lower():
                print("      Vérifiez l'installation de Java et la variable JAVA_HOME.")
            problems.append("session")

    # --- 5. Fichier volumineux de la séance 7 ------------------------------
    print(f"\n{BOLD}5. Données de la séance 7{RESET}")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    big_file = os.path.join(base, "data", "raw", "evenements_volumineux.csv")
    if os.path.exists(big_file):
        size_mb = os.path.getsize(big_file) / (1024 ** 2)
        ok(f"evenements_volumineux.csv présent ({size_mb:.0f} Mo)")
    else:
        warn("evenements_volumineux.csv absent",
             "À générer AVANT la séance (3 à 5 minutes) :\n"
             "      python src/generate_data.py --big 5000000")

    # --- Conclusion --------------------------------------------------------
    print("\n" + "=" * 72)
    if not problems:
        print(f"{GREEN}{BOLD}Tout est prêt pour la séance 7.{RESET}\n")
        return 0

    print(f"{RED}{BOLD}{len(problems)} point(s) à corriger avant la séance.{RESET}")
    print("Reprenez les lignes marquées ECHEC ci-dessus, dans l'ordre : "
          "Java d'abord,\nPySpark ensuite. Relancez ce script après chaque correction.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
