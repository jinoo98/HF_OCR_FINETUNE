import os
import json
import shutil

def split_dataset():
    base_dir = "dataset"
    jsonl_path = os.path.join(base_dir, "jsonl", "results_with_QA.jsonl")
    
    # If results_with_QA.jsonl doesn't exist, fallback to results.jsonl
    if not os.path.exists(jsonl_path):
        jsonl_path = os.path.join(base_dir, "jsonl", "results.jsonl")
        if not os.path.exists(jsonl_path):
            print(f"Error: No jsonl file found in {base_dir}/jsonl")
            return

    with open(jsonl_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"Total JSONL entries: {len(lines)}")
    
    # Splitting logic -> 200, 200, 200, and the rest (227)
    chunk_sizes = [200, 200, 200]

    output_base = "example"
    if not os.path.exists(output_base):
        os.makedirs(output_base)

    def get_part_dir(part_num):
        return os.path.join(output_base, f"part{part_num}")

    # Prepare directories
    for part in range(1, 5):
        os.makedirs(os.path.join(get_part_dir(part), "images"), exist_ok=True)
        os.makedirs(os.path.join(get_part_dir(part), "jsonl"), exist_ok=True)

    part_number = 1
    current_target = chunk_sizes[part_number - 1]
    items_in_current_part = 0
    
    output_files = {
        i: open(os.path.join(get_part_dir(i), "jsonl", os.path.basename(jsonl_path)), "w", encoding="utf-8") 
        for i in range(1, 5)
    }

    for line in lines:
        if part_number < 4 and items_in_current_part >= current_target:
            part_number += 1
            if part_number < 4:
                current_target = chunk_sizes[part_number - 1]
            items_in_current_part = 0
            
        output_files[part_number].write(line + "\n")
        
        data = json.loads(line)
        if "image_info" in data and len(data["image_info"]) > 0:
            img_url = data["image_info"][0].get("image_url", "")
            if img_url:
                filename = os.path.basename(img_url)
                src_img = os.path.join(base_dir, "images", filename)
                dst_img = os.path.join(get_part_dir(part_number), "images", filename)
                
                if os.path.exists(src_img):
                    shutil.copy2(src_img, dst_img)
                else:
                    print(f"Warning: Image {src_img} not found.")

        items_in_current_part += 1

    for f in output_files.values():
        f.close()
        
    print(f"Dataset securely split into {output_base}/part1, part2, part3, part4.")
    
if __name__ == "__main__":
    split_dataset()
