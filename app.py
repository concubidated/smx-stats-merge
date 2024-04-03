from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import sys, os, shutil
from lxml import etree as et
import tempfile
import zipfile

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file1' not in request.files or 'file2' not in request.files:
            return "No file"
        file1 = request.files['file1']
        file2 = request.files['file2']

        # Save the uploaded ZIP file
        zip1_filename = (file1.filename)
        zip1_path = os.path.join(app.config['UPLOAD_FOLDER'], zip1_filename)
        file1.save(zip1_path)

        temp_dir_1 = extract_zip_to_temp_dir(zip1_path)

        # Save the uploaded ZIP file
        zip2_filename = secure_filename(file2.filename)
        zip2_path = os.path.join(app.config['UPLOAD_FOLDER'], zip2_filename)
        file2.save(zip2_path)

        temp_dir_2 = extract_zip_to_temp_dir(zip2_path)

        temp1_path = os.path.join(temp_dir_1, 'Save/MachineProfile/Stats.xml')
        with open(temp1_path, 'rb') as f:
            stats1 = f.read()

        temp2_path = os.path.join(temp_dir_2, 'Save/MachineProfile/Stats.xml')
        with open(temp2_path, 'rb') as f:
            stats2 = f.read()

        #do the thing
        merged_stats = stats_merge(stats1, stats2)

        # overwrite the stats file
        with open(temp1_path, 'wb') as f:
            f.write(merged_stats)

        new_zip_path = zip_directory(temp_dir_1, zip1_path)

        # Send the ZIP file as a response
        return send_file(new_zip_path, as_attachment=True, download_name='StepManiaX_backup (merged).zip')

def extract_zip_to_temp_dir(zip_file_path):
    try:
        # Create a temporary directory to extract files
        temp_dir = tempfile.mkdtemp()
        # Extract the ZIP archive to the temporary directory
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        return temp_dir
    except Exception as e:
        print(f"Error extracting ZIP file: {str(e)}")
        return None

def zip_directory(temp_dir, original_zip_path):
    try:
        # Create a new ZIP archive with the contents of the temporary directory
        updated_zip_path = original_zip_path.replace('.zip', ' (merged).zip')
        with zipfile.ZipFile(updated_zip_path, 'w') as zip_ref:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arcname)
        return updated_zip_path
    except Exception as e:
        print(f"Error re-zipping directory: {str(e)}")
        return None

def stats_merge(file1, file2):


    #noticed some songs names are not UTF-8 encoded
    parser = et.XMLParser(encoding='UTF-8')
    root1 = et.fromstring(file1,parser)
    root2 = et.fromstring(file2,parser)

    songData = root1.find("SongScores")
    diffTypes = {}
    stepTypes = {}

    for song in songData:
        diffTypes = {}
        stepTypes = {}
        song_name = song.attrib['Dir']
        #print(song_name)
        
        song_new = root2.xpath(f'/Stats/SongScores/Song[@Dir="{song_name}"]')

        if len(song_new) > 0:
            song_new = song_new[0]
        
        oldSteps = song.findall("Steps")
        score = 0
        score_new = 0
        for steps in oldSteps:
            
            diff = steps.attrib['Difficulty']
            step = steps.attrib['StepsType']

            if len(song_new) > 0:
                steps_new = song_new.xpath("./Steps[@Difficulty='{}'][@StepsType='{}']".format(diff, step))
                highscore_new = None
                if len(steps_new) > 0:
                    steps_new = steps_new[0]
                    highscore_new = steps_new.xpath("./StepsStats/HighScore")
                    if len(highscore_new) > 0:
                        highscore_new = highscore_new[0]
                    else:
                        highscore_new = None

                stepstats = steps.find("StepsStats")
                highscore = stepstats.find("HighScore")


                if highscore is not None and highscore_new is not None:
                    score = int(highscore.find("Score").text)
                    score_new = int(highscore_new.find("Score").text)

                    if score_new > score:
                        #name = highscore_new.find("Name").text
                        #print(name, diff, step, score_new, "is higher then", score)

                        parent = highscore.getparent()
                        parent.replace(highscore, highscore_new)

                if highscore is None and highscore_new is not None:
                        stepstats.append(highscore_new)

    content = et.tostring(root1, encoding='utf-8', method='xml')
    return content

if __name__ == '__main__':
    app.run(debug=True)