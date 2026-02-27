import sys, traceback
sys.path.append('/app')
print('RUN_SYNC START')
try:
    from worker import process_document
    print('FOUND', process_document)
    process_document.run('/app/uploads/327fde68-460a-4cfd-870d-a636e3e51cd1_TeaQulture.txt', 'TeaQulture.txt', 'txt', 111)
    print('PROCESS COMPLETE')
except Exception as e:
    traceback.print_exc()
    print('ERROR', e)
