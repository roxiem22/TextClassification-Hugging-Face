# -*- coding: utf-8 -*-
"""Untitled0.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1l52luhk6uavH8-wpXhuiIZ3wZ4btaj_l
"""

! pip install datasets transformers[sentencepiece]

from datasets import load_dataset
raw_datasets = load_dataset("sst2")
raw_datasets.cache_files

raw_datasets.save_to_disk("my-arrow-datasets")

from datasets import load_from_disk

arrow_datasets_reloaded = load_from_disk("my-arrow-datasets")
arrow_datasets_reloaded

for split, dataset in raw_datasets.items():
    dataset.to_csv(f"my-dataset-{split}.csv", index=None)

data_files = {
    "train": "my-dataset-train.csv",
    "validation": "my-dataset-validation.csv",
    "test": "my-dataset-test.csv",
}

csv_datasets_reloaded = load_dataset("csv", data_files=data_files)
csv_datasets_reloaded

# Save in JSON Lines format
for split, dataset in raw_datasets.items():
    dataset.to_json(f"my-dataset-{split}.jsonl")

# Save in Parquet format
for split, dataset in raw_datasets.items():
    dataset.to_parquet(f"my-dataset-{split}.parquet")

json_data_files = {
    "train": "my-dataset-train.jsonl",
    "validation": "my-dataset-validation.jsonl",
    "test": "my-dataset-test.jsonl",
}

parquet_data_files = {
    "train": "my-dataset-train.parquet",
    "validation": "my-dataset-validation.parquet",
    "test": "my-dataset-test.parquet",
}

# Reload with the `json` script
json_datasets_reloaded = load_dataset("json", data_files=json_data_files)
# Reload with the `parquet` script
parquet_datasets_reloaded = load_dataset("parquet", data_files=parquet_data_files)

from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')

from transformers import AutoModelForSequenceClassification

model = AutoModelForSequenceClassification.from_pretrained(
    'distilbert-base-uncased-finetuned-sst-2-english',
    num_labels=2
)

import pandas as pd
df = pd.read_csv('/content/my-dataset-train.csv')
df.head()

import torch
import torch.nn.functional as F
def process_data(row):
  
    text = row['sentence']
    text = str(text)
    text = ' '.join(text.split())

    encodings = tokenizer(text, padding='max_length', truncation=True, max_length=512)
   
    val = 0
    if row['label'] == 1:
      val = 1

    encodings['labels'] = val

    return encodings

processed_data = []

for i in range(10000):
    processed_data.append(process_data(df.iloc[i]))

from sklearn.model_selection import train_test_split

new_df = pd.DataFrame(processed_data)

train_df, valid_df = train_test_split(
    new_df,
    test_size=0.2,
    random_state=22
)

print(train_df)

import pyarrow as pa
from datasets import Dataset
from torch.utils.data import DataLoader

train_hg = Dataset(pa.Table.from_pandas(train_df,preserve_index=False))
valid_hg = Dataset(pa.Table.from_pandas(valid_df,preserve_index=False))

pip install transformers accelerate

from transformers import AdamW

device = torch.device("cuda")
model.to(device)
optimizer = AdamW(model.parameters(), lr=2e-5)
epochs = 2 

for epoch in range(epochs):
    model.train()
    for batch in train_hg:
        inputs = {"input_ids": torch.tensor(batch['input_ids']).to(device), "attention_mask": torch.tensor(batch['attention_mask']).to(device), "labels": torch.tensor(batch['labels']).to(device)}
        outputs = model(**inputs)
        loss = outputs.loss
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

    model.eval()
    valLoss = 0
    with torch.no_grad():
      for batch in valid_hg:
            inputs = {"input_ids": torch.tensor(batch['input_ids']).to(device), "attention_mask": torch.tensor(batch['attention_mask']).to(device), "labels": torch.tensor(batch['labels']).to(device)}
            outputs = model(**inputs)
            loss = outputs.loss
            valLoss += loss.item()
            
    valLoss /= len(valid_hg)

    print(f"Epoch no {epoch+1}")
    print(f"Validation Loss: {valLoss:.5f}")

path = "/model.pth"
torch.save(model.state_dict(), path)

import torch
import numpy as np

def get_prediction(text):
    encoding = tokenizer.encode_plus(text, return_tensors="pt", padding="max_length", truncation=True, max_length=128)
    encoding = {k: v.to(model.device) for k, v in encoding.items()} 

    outputs = model(**encoding)

    logits = outputs.logits
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    sigmoid = torch.nn.Sigmoid()
    print(sigmoid)
    probs = sigmoid(logits.squeeze().cpu())
    probs = probs.detach().numpy()
    label = np.argmax(probs, axis=-1)
    
    if label == 1:
        return {
            'label': 'Positive',
            'probability': probs[1]
        }
    else:
        return {
            'label': 'Negative',
            'probability': probs[0]
        }

get_prediction('I am happy.')