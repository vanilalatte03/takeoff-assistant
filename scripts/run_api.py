"""Run the local API with an explicitly selected external environment file."""
from argparse import ArgumentParser
import os
from pathlib import Path
import sys


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--vision-use-search-model', action='store_true', help='Use the configured search model for images in this process only; requires image support')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--reload', action='store_true')
    args = parser.parse_args()
    if not args.env_file.is_file():
        parser.error('Environment file does not exist')
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=False, interpolate=False)
    if args.vision_use_search_model and not os.environ.get('TAKEOFF_AI_VISION_MODEL'):
        os.environ['TAKEOFF_AI_VISION_MODEL'] = os.environ.get('TAKEOFF_AI_MODEL','')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/api'))
    import uvicorn
    uvicorn.run('app.main:app',host='127.0.0.1',port=args.port,reload=args.reload)


if __name__=='__main__':
    main()
