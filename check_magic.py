try:
    import magic
    print("python-magic is installed")
except ImportError:
    print("python-magic is NOT installed - file validation will be limited")
