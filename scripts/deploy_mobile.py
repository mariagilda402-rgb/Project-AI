"""
Deploy Mobile PWA to GitHub Pages (gh-pages branch).

Usage:
    python scripts/deploy_mobile.py

Flow:
    1. Copies mobile/ to a temp directory
    2. Force-pushes to gh-pages branch
    3. GitHub Pages auto-serves the content
    4. User accesses: https://<user>.github.io/<repo>/
"""
import subprocess, shutil, tempfile, os, sys

MOBILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mobile")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run(cmd, cwd=None, check=True):
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or REPO_ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    if result.returncode != 0 and check:
        print(f"    ERRO: {result.stderr.strip()}")
        sys.exit(1)
    return result

def main():
    print("=" * 50)
    print("  DEPLOY MOBILE PWA -> GitHub Pages")
    print("=" * 50)

    # Get remote URL
    r = run("git remote get-url origin")
    remote_url = r.stdout.strip()
    print(f"\n[1/5] Remote: {remote_url}")

    # Create temp dir and copy mobile files
    tmp = tempfile.mkdtemp(prefix="nexus_deploy_")
    print(f"[2/5] Copiando mobile/ -> {tmp}")
    
    for item in os.listdir(MOBILE_DIR):
        s = os.path.join(MOBILE_DIR, item)
        d = os.path.join(tmp, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    # Init git in temp, create gh-pages branch, force push
    print("[3/5] Inicializando git na pasta temporaria...")
    run("git init", cwd=tmp)
    run("git checkout -b gh-pages", cwd=tmp)
    run("git add -A", cwd=tmp)
    run('git commit -m "Deploy Mobile PWA"', cwd=tmp)
    
    print("[4/5] Enviando para GitHub (gh-pages)...")
    run(f'git remote add origin "{remote_url}"', cwd=tmp)
    run("git push origin gh-pages --force", cwd=tmp)

    # Cleanup
    print("[5/5] Limpando temporarios...")
    shutil.rmtree(tmp, ignore_errors=True)

    # Derive GitHub Pages URL
    # https://github.com/user/repo.git -> https://user.github.io/repo/
    parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")
    if len(parts) >= 2:
        user, repo = parts[0], parts[1]
        pages_url = f"https://{user}.github.io/{repo}/"
        print(f"\n{'=' * 50}")
        print(f"  DEPLOY CONCLUIDO!")
        print(f"  Acesse no celular: {pages_url}")
        print(f"{'=' * 50}")
    else:
        print("\nDeploy concluido! Verifique as configuracoes do GitHub Pages.")

if __name__ == "__main__":
    main()
