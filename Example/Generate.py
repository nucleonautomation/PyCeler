import argparse
import hashlib
import json
import sys
from pathlib import Path
# Prefer the checkout's verified build when this script is run from the repository.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import PyCeler

def Main():
    # Static conversion is the catalogue default; measured selection is an explicit executable workload.
    Parser = argparse.ArgumentParser(description='Generate readable Cython; bulk example outputs go to ignored Test_Run/Examples.')
    Parser.add_argument('--name', action='append', help='Example name from Manifest.json; repeat to select several.')
    Parser.add_argument('--measured', action='store_true', help='Enable validation/timing selection; this can execute candidate workloads.')
    Args = Parser.parse_args()
    Folder = Path(__file__).resolve().parent
    Manifest_File = Folder / 'Manifest.json'
    Manifest = json.loads(Manifest_File.read_text(encoding='utf-8'))
    Names = set(Args.name or [Entry['Name'] for Entry in Manifest['Examples']])
    Known = {Entry['Name'] for Entry in Manifest['Examples']}
    if Names - Known:
        Parser.error('Unknown examples: ' + ', '.join(sorted(Names - Known)))
    for Entry in Manifest['Examples']:
        if Entry['Name'] not in Names:
            continue
        Source = Folder / Entry['Python']
        # Keep bulk example folders source-only; generated code and selection reports are disposable artifacts.
        Destination = Folder.parent / 'Test_Run/Examples' / Entry['Category'] if Entry['Category'] in ('Loops', 'Benchmarks') else Source.parent
        Generated = PyCeler.Convert(Source, Destination, Select=Args.measured, OpenMP=True)
        Entry['Cython'] = '../Test_Run/Examples/' + Entry['Category'] + '/' + Generated.name if Entry['Category'] in ('Loops', 'Benchmarks') else Generated.name
        Entry['Generated_Present'] = True
        Text = Generated.read_text(encoding='utf-8')
        if '_Pyceler_Baseline(' in Text or '_Pyceler_Python_Builtins.exec(' in Text:
            raise RuntimeError('Generated source contains an executable source wrapper: ' + str(Generated))
        Entry['Python_SHA256'] = hashlib.sha256(Source.read_bytes()).hexdigest()
        Entry['Cython_SHA256'] = hashlib.sha256(Generated.read_bytes()).hexdigest()
        Entry['Generation'] = dict(Build_Id=PyCeler.__build_id__, Select=Args.measured, OpenMP=True)
        Entry['Validation']['Cython_Translation'] = 'pending'
        Entry['Validation']['Executed'] = False
        Entry['Validation'].pop('Native_Smoke', None)
        # Save progress after each file so an interrupted large catalogue can be resumed by name.
        Manifest_File.write_text(json.dumps(Manifest, indent=2), encoding='utf-8')
        print(Entry['Name'] + ': ' + Entry['Cython'], flush=True)
    Choices = {Entry.get('Generation', {}).get('Select') for Entry in Manifest['Examples']}
    Manifest['Generation'] = dict(Build_Id=PyCeler.__build_id__, Select=Choices.pop() if len(Choices) == 1 else 'mixed', OpenMP=True, Status='generated' if all('Cython_SHA256' in Entry for Entry in Manifest['Examples']) else 'partial')
    Manifest['Validation_Summary'] = {Status: sum(Entry['Validation']['Cython_Translation'] == Status for Entry in Manifest['Examples']) for Status in ('passed', 'failed', 'pending')}
    Manifest_File.write_text(json.dumps(Manifest, indent=2), encoding='utf-8')

if __name__ == '__main__':
    Main()
