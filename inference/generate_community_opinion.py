"""

This script uses communuty GPT models to generate opinions given prompts and save these
voices

"""

from transformers import pipeline, set_seed
import os
import pandas as pd
import argparse
import tqdm
import torch
from pathlib import Path


def generate_with_a_prompt(prompt, text_gen_pipeline):
    """
    Generate a list of statements given the prompt based on one GPT-2 model

    NOTE: 50256 corresponds to '<|endoftext|>'
    """

    results = text_gen_pipeline(
        prompt,
        do_sample=True,
        truncation=True,
        max_length=50,
        temperature=1.0,
        num_return_sequences=100,  # 1000 leads to OOM
        pad_token_id=50256,
        clean_up_tokenization_spaces=True,
    )

    # only use the first utterance
    results = [res["generated_text"].split("\n")[0] for res in results]
    return results


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str)
    parser.add_argument("--prompt_data_path", type=str)
    parser.add_argument("--prompt_option", type=str)
    parser.add_argument("--preceding_prompt", default=None, type=str)
    parser.add_argument("--output_path", type=str)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    set_seed(args.seed)

    df = pd.read_csv(args.prompt_data_path)
    questions = df.pid.values.tolist()
    prompts = df[args.prompt_option].values.tolist()
    mps_device = torch.device("mps")
    text_generator = pipeline(
        "text-generation", model=args.model_path, device=mps_device
    )

    output_folder = os.path.join(args.output_path, args.prompt_option)
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    for question_id, (question, prompt) in enumerate(zip(questions, prompts)):
        responses = []
        print(f"Working on [{question}] ({question_id}/{len(questions)})...")
        for _ in tqdm.tqdm(range(10)):
            if args.preceding_prompt:
                batch_responses = generate_with_a_prompt(
                    " ".join([args.preceding_prompt, prompt]), text_generator
                )
            else:
                batch_responses = generate_with_a_prompt(prompt, text_generator)
            responses.extend(batch_responses)

        with open(os.path.join(output_folder, question + ".txt"), "w") as out:
            for line in responses:
                line = line.replace("\n", " ")
                if args.preceding_prompt:
                    line = line.replace(args.preceding_prompt + " ", "")
                out.write(line)
                out.write("\n")


if __name__ == "__main__":
    main()
