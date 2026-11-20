import argparse
import ast
import contextlib
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyCeler.Native_Build import _Cython_Compatibility

def Main():
    # Translation checks the complete catalogue without running its large workloads or external callbacks.
    Parser = argparse.ArgumentParser(description='Check Python syntax and translate example outputs created by Generate.py.')
    Parser.add_argument('--name', action='append', help='Check only these example names; default is the complete catalogue.')
    Args = Parser.parse_args()
    Folder = Path(__file__).resolve().parent
    Manifest_File = Folder / 'Manifest.json'
    Manifest = json.loads(Manifest_File.read_text(encoding='utf-8'))
    Names = set(Args.name or [Entry['Name'] for Entry in Manifest['Examples']])
    Unknown = Names - {Entry['Name'] for Entry in Manifest['Examples']}
    if Unknown:
        Parser.error('Unknown examples: ' + ', '.join(sorted(Unknown)))
    Runs = Folder.parent / 'Test_Run'
    Runs.mkdir(exist_ok=True)
    Output = Path(tempfile.mkdtemp(prefix='Example_Validation_', dir=Runs))
    from Cython.Compiler.Main import CompilationOptions, compile as Translate, default_options
    Failures = []
    Results = []
    for Entry in Manifest['Examples']:
        if Entry['Name'] not in Names:
            continue
        Source, Generated = Folder / Entry['Python'], Folder / Entry['Cython']
        ast.parse(Source.read_text(encoding='utf-8'), filename=str(Source))
        if not Generated.is_file():
            Parser.error('Generated output is absent for ' + Entry['Name'] + '; run python Example/Generate.py --name ' + Entry['Name'] + ' first (omit --name to generate all).')
        if hashlib.sha256(Source.read_bytes()).hexdigest() != Entry['Python_SHA256']:
            raise RuntimeError('Python source changed; regenerate first: ' + str(Source))
        if hashlib.sha256(Generated.read_bytes()).hexdigest() != Entry['Cython_SHA256']:
            raise RuntimeError('Cython source changed; regenerate or update its provenance: ' + str(Generated))
        Diagnostics = io.StringIO()
        Options = CompilationOptions(default_options, output_file=str(Output / (Entry['Name'] + '.c')), compiler_directives=dict(language_level=3, annotation_typing=False, infer_types=False, binding=True), include_path=[str(Generated.parent)])
        with contextlib.redirect_stderr(Diagnostics), _Cython_Compatibility():
            Result = Translate(str(Generated), options=Options, full_module_name=Generated.stem)
        Status = 'passed' if Result.num_errors == 0 else 'failed'
        Entry['Validation']['Cython_Translation'] = Status
        Entry['Validation']['Expected_Translation_Failure'] = bool(Result.num_errors and Entry.get('Known_Limitation'))
        (Output / (Entry['Name'] + '.log')).write_text(Diagnostics.getvalue(), encoding='utf-8')
        Results.append(dict(Name=Entry['Name'], Errors=Result.num_errors))
        if Result.num_errors:
            Failures.append(Entry['Name'])
        Manifest_File.write_text(json.dumps(Manifest, indent=2), encoding='utf-8')
        print(Entry['Name'] + ': ' + Status, flush=True)
    (Output / 'Results.json').write_text(json.dumps(dict(Verification='Python syntax and Cython-to-C translation; no benchmark execution', Results=Results), indent=2), encoding='utf-8')
    Manifest['Validation_Summary'] = {Status: sum(Entry['Validation']['Cython_Translation'] == Status for Entry in Manifest['Examples']) for Status in ('passed', 'failed', 'pending')}
    Manifest_File.write_text(json.dumps(Manifest, indent=2), encoding='utf-8')
    print('Translation report: ' + str(Output / 'Results.json'), flush=True)
    return 1 if Failures else 0

if __name__ == '__main__':
    raise SystemExit(Main())
