#!/usr/bin/env python3

from openai import OpenAI
import argparse
import json
import os


# Set up logging
import logging
from rich.logging import RichHandler
logging.basicConfig(
    level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )
log = logging.getLogger("transcribe_with_llm")


# Helper image pre processing functions
def preprocess_image(image_path, dir_for_processed_images):
    
    # Used to prepare the image for processing with the OPENAI API.
    # First, the image should always be in portrait mode, thus we check the orientation and create 2 rotated versions of the image,
    # one rotated 90 degrees clockwise and another rotated 90 degrees counter-clockwise. The process them both and determine which one returns the label text.
    from PIL import ImageOps, Image
    os.makedirs(os.path.join(dir_for_processed_images,'fullsize'), exist_ok=True)
    image = ImageOps.exif_transpose(Image.open(image_path))
    if image.width > image.height:
        # If the image is in landscape mode, rotate it 90 degrees clockwise and counter-clockwise
        rotated_image_cw = image.rotate(-90, expand=True)
        rotated_image_ccw = image.rotate(90, expand=True)
        # Save the full size rotated images to the fullsize directory
        fullsize_cw_path = os.path.join(dir_for_processed_images, 'fullsize', os.path.basename(image_path.replace(".jpg", "_cw.jpg").replace(".png", "_cw.png")))
        fullsize_ccw_path = os.path.join(dir_for_processed_images, 'fullsize', os.path.basename(image_path.replace(".jpg", "_ccw.jpg").replace(".png", "_ccw.png")))
        rotated_image_cw.save(fullsize_cw_path)
        rotated_image_ccw.save(fullsize_ccw_path)
        # We know that the text to transcribe is always in the bottom half of the image, so we crop it to that area.
        rotated_image_cw_cropped = rotated_image_cw.crop((0, rotated_image_cw.height // 2, rotated_image_cw.width, rotated_image_cw.height))
        rotated_image_ccw_cropped = rotated_image_ccw.crop((0, rotated_image_ccw.height // 2, rotated_image_ccw.width, rotated_image_ccw.height))
        # Save both rotated images to preprocessed files
        cw_path = os.path.join(dir_for_processed_images, os.path.basename(image_path.replace(".jpg", "_cw.jpg").replace(".png", "_cw.png")))
        ccw_path = os.path.join(dir_for_processed_images, os.path.basename(image_path.replace(".jpg", "_ccw.jpg").replace(".png", "_ccw.png")))
        rotated_image_cw_cropped.save(cw_path)
        rotated_image_ccw_cropped.save(ccw_path)
        processed_image_path = [cw_path, ccw_path]
    else:
        # If the image is already in portrait mode, we again have 2 version, one original and one rotated 180 degrees.
        rotated_image = image.rotate(180, expand=True)
        # Save the full size rotated image to the fullsize directory
        fullsize_rotated_path = os.path.join(dir_for_processed_images, 'fullsize', os.path.basename(image_path.replace(".jpg", "_rotated.jpg").replace(".png", "_rotated.png")))
        rotated_image.save(fullsize_rotated_path)
        # Save the original image to the fullsize directory
        fullsize_original_path = os.path.join(dir_for_processed_images, 'fullsize', os.path.basename(image_path.replace(".jpg", "_original.jpg").replace(".png", "_original.png")))
        image.save(fullsize_original_path)
        # Crop the bottom half of the original image
        width, height = image.size
        cropped_image = image.crop((0, height // 2, width, height))
        # crop the bottom half of the rotated image
        rotated_image_cropped = rotated_image.crop((0, rotated_image.height // 2, rotated_image.width, rotated_image.height))
        # Save both cropped images to preprocessed files
        original_path = os.path.join(dir_for_processed_images, os.path.basename(image_path.replace(".jpg", "_original.jpg").replace(".png", "_original.png")))
        rotated_path = os.path.join(dir_for_processed_images, os.path.basename(image_path.replace(".jpg", "_rotated.jpg").replace(".png", "_rotated.png")))
        cropped_image.save(original_path)
        rotated_image_cropped.save(rotated_path)
        processed_image_path = [original_path, rotated_path]
    return processed_image_path

client = OpenAI()

# Function to create a file with the Files API
def create_file_for_openai(file_path):
  with open(file_path, "rb") as file_content:
    result = client.files.create(
        file=file_content,
        purpose="vision",
    )
    return result.id


# Main function
# This function gets a directory of images as an argument, processes each image, and sends it to the OpenAI API for transcription.
# The output for each image is saved in a json file in the subdirectory "transcriptions".
# Additionally, the processed images are saved, named as their ID extracted from the OpenAI API response, together with the original file name
# in the subdirectory "processed_images".
def main():
    parser = argparse.ArgumentParser(description="Transcribe images using OpenAI API.")
    parser.add_argument("image_path", type=str, help="Path to the image file or directory containing images.")
    parser.add_argument("--processed_images_dir", type=str, default="processed_images", help="Directory to save processed images.")
    parser.add_argument("--transcriptions_dir", type=str, default="transcriptions", help="Directory to save transcriptions.")
    parser.add_argument("--orientated_images_dir", type=str, default="orientated_images", help="Directory to save orientated images.")
    parser.add_argument("--override", action="store_true", help="Override existing files in the processed images and transcriptions directories.")
    args = parser.parse_args()

    image_path = args.image_path
    processed_images_dir = args.processed_images_dir
    transcriptions_dir = args.transcriptions_dir
    orientated_images_dir = args.orientated_images_dir
    override = args.override
    
    # print the raw command line call
    import sys    
    log.info(f"Command line call: {sys.argv[0]} {image_path} --processed_images_dir {processed_images_dir} --transcriptions_dir {transcriptions_dir} --orientated_images_dir {orientated_images_dir} {'--override' if override else ''}")
    
    # Create directories if they don't exist
    import os
    os.makedirs(processed_images_dir, exist_ok=True)
    os.makedirs(transcriptions_dir, exist_ok=True)
    os.makedirs(orientated_images_dir, exist_ok=True)
    
    # Main processing loop, iterating over all images in the specified directory
    if os.path.isdir(image_path):
        import glob
        image_files = glob.glob(os.path.join(image_path, "*.jpg")) + glob.glob(os.path.join(image_path, "*.png"))
    else:
        raise ValueError(f"Provided path {image_path} is not a directory.")
    
    for image_file in image_files:
        # Check if the image has already been processed, and if so, skip it unless override is set
        image_file_base = os.path.splitext(os.path.basename(image_file))[0]
        if not override:
            flag_file_path = os.path.join(processed_images_dir, 'processed', f"{image_file_base}.processed")
            if os.path.exists(flag_file_path):
                log.info(f"Skipping already processed image: {image_file}")
                continue
        log.info(f"Processing image: {image_file}")
        
        # Preprocess the image
        pre_processed_image_paths = preprocess_image(image_file, processed_images_dir)
        if not pre_processed_image_paths:
            log.info(f"Skipping image {image_file} as it could not be preprocessed.")
            continue
        # We have two preprocessed images, one of them is valid and the other is rotated 180 degrees.
        # We will try to transcribe both images, and if one of them returns a valid transcription, we will use it.
        if not len(pre_processed_image_paths) == 2:
            log.info(f"Skipping image {image_file} as it could not be preprocessed correctly.")
            continue
        # Run the OpenAI API 2 times to transcribe the image
        transcriptions = []
        for pre_processed_image_path in pre_processed_image_paths:
            log.info(f"Transcribing image: {pre_processed_image_path}")
            # Check if the file exists
            if not os.path.exists(pre_processed_image_path):
                log.info(f"File {pre_processed_image_path} does not exist, skipping.")
                continue

            # Create a file in OpenAI's Files API
            file_id = create_file_for_openai(pre_processed_image_path)
            # Prepare the prompt for the OpenAI API    
            #prompt = """
            #Can you recognize the text, handwriting and written, from this image? The label has botanical context.
            #"""

            prompt = """Please transcribe the text in label of the image. The label is located in the bottom half of the image.
            and the text is in English. The text contains botanical context, but it is not required to understand the transcription.
            When transcribing, please ignore any other text that is not in the bottom half of the image. Produce the output in JSON format.
            If there is no text in the image containing the label, return a JSON object where the fields are empty, set to "". 
            The JSON should have the following structure:
            {
                "label": {
                    "district": "District or region, can be named Regio",
                    "Grid reference": "Grid reference, can be named Grid.Ref, if not available, leave empty",
                    "Date": "Date of collection, can be named Date, or Anno. Use the format YYYY-MM-DD",
                    "Altitude": "Altitude, can be named Alt., or Altitude, or Elevation. Use the format 1234 m. Can be empty if not available",
                    "collector_name": "Name of the collector, can be named Coll., or Collectors. Leave empty if not available",
                    "collector_number": "Collector number, can be named Collector's No., or Collector No., or Collector's Number. Leave empty if not available",
                    "name": "Name of the plant, located in the upper part of the label, but below the fields described above.",
                    "description": "Description of the plant, located below the name, in the lower part of the label. Separated by a line or empty space from the name. For multiple lines, use \\n to separate them.",
                    "plant_id": "Separate label, with a barcode on top of it, the text is under the barcode. Starts with SRGH. Can be rotated 90 degrees, located either above or beside the main label.",
                },
                "extracted_metadata": {
                    "Habitat": "Habitat information, extract it from the free text description, if possible, otherwise leave empty",
                    "Geographic_information": "Geographic information, extract it from the free text description, if possible, otherwise leave empty",
                    "Flowering state": "Flowering state, extract it from the free text description, if possible, otherwise leave empty",
                    "Phenotype": "Any phenotype-related information, extract it from the free text description, if possible, otherwise leave empty.",
                }
            }
            There are multiple types of labels, the text is always in the bottom half of the image, but the fields may vary.
            The structured fields are always in the top half of the label, and the free text description is in the bottom half.
            The text is in English, but it may contain some botanical terms that are not in English.
            """        

            # Create a response using the OpenAI API
            response = client.responses.create(
                model="gpt-4o",
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "file_id": file_id,
                        },
                    ],
                }],
            )
            # Parse the response and save the transcription
            transcription = response.output_text.strip()
            log.info(transcription)
            transcription_dict = json.loads(transcription.strip('```json\n').rstrip('```'))
            # Add the preprocessed image path to the transcription dictionary
            transcription_dict['image_path'] = pre_processed_image_path
            # Add the transcription to the list of transcriptions
            transcriptions.append(transcription_dict)

        # Compare which transcription is better, if both are valid, we will use the one with the most fields filled.
        if not transcriptions:
            log.info(f"No valid transcriptions found for image {image_file}.")
            continue
        # Select the transcription with the most fields filled
        best_transcription = max(transcriptions, key=lambda t: sum(1 for v in t['label'].values() if v) + sum(1 for v in t['extracted_metadata'].values() if v))

        # Replace special characters in the plant id with underscores (, spaces, dashes, etc.)
        import re
        plant_id = re.sub(r'[^\w]', '_', best_transcription['label']['plant_id'])
        # Update the plant_id in the transcription dictionary
        best_transcription['label']['plant_id'] = plant_id
        

        # Save the best transcription to a JSON file
        transcription_dict = best_transcription
        image_file_base = os.path.splitext(os.path.basename(image_file))[0]
        transcription_file_path = os.path.join(transcriptions_dir, f"{image_file_base}.{transcription_dict['label']['plant_id']}.json")
        # Save the transcription to a JSON file, pretty printed
        with open(transcription_file_path, "w") as transcription_file:
            json.dump(transcription_dict, transcription_file, indent=4)
        log.info(best_transcription)
        log.info(f"Transcription saved to {transcription_file_path}")
        # Save the image with the correct orientation to the orientated images directory
        orientated_image_path = os.path.join(orientated_images_dir, f"{image_file_base}.{transcription_dict['label']['plant_id']}.jpg")
        # Copy the correct image to the orientated images directory
        from shutil import copyfile
        # Construct the source image path, it should include the full_size directory
        fullsize_image_path = os.path.join(processed_images_dir, 'fullsize', os.path.basename(best_transcription['image_path']))
        copyfile(fullsize_image_path, orientated_image_path)
        # Copy the cropped image to the processed images directory
        processed_image_path = os.path.join(processed_images_dir + '_orientated', f"{image_file_base}.{transcription_dict['label']['plant_id']}.jpg")
        os.makedirs(os.path.dirname(processed_image_path), exist_ok=True)
        copyfile(best_transcription['image_path'], processed_image_path)
        # Create flag file to indicate that the image has been processed, using only the image file name without the extension, write the timestamp to the file
        import time
        flag_file_path = os.path.join(processed_images_dir, 'processed', f"{image_file_base}.processed")
        os.makedirs(os.path.dirname(flag_file_path), exist_ok=True)
        with open(flag_file_path, "w") as flag_file:
            flag_file.write("Processed at: " + time.strftime("%Y-%m-%d %H:%M:%S"))




if __name__ == "__main__":
    main()