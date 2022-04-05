from typing import Any, List
import asyncio
import json
import logging
import os

from albumentations import Compose, LongestMaxSize, Normalize, PadIfNeeded
from albumentations.pytorch import ToTensorV2
import cv2
import streamlit as st
import torch
import PIL
import numpy as np

tg_api_token = '2139541049:AAF4-8-FuOCTnjYkCG5yjyAQgAlg9DR65nU'
tg_chat_id = '1282687859'
import requests
def send_tg_msg(text='Cell execution completed.'):
    requests.post(
        'https://api.telegram.org/' +
        'bot{}/sendMessage'.format(tg_api_token), 
        params=dict(chat_id=tg_chat_id, text=text)
    )
class ClassifyModel:
    def __init__(self):
        self.model = None
        self.class2tag = None
        self.tag2class = None
        self.transform = None

    def load(self, path="/model"):
        image_size = 512
        self.transform = Compose(
            [
                LongestMaxSize(max_size=image_size),
                PadIfNeeded(image_size, image_size, border_mode=cv2.BORDER_CONSTANT),
                Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225), always_apply=True),
                ToTensorV2()
            ]
        )
        self.model = torch.jit.load("model_healthy_bot.pth")
        with open("tag2class_healthy_bot.json") as fin:
            self.tag2class = json.load(fin)
            self.class2tag = {v: k for k, v in self.tag2class.items()}
            logging.debug(f"class2tag: {self.class2tag}")

    def predict(self, *imgs) -> List[str]:
        logging.debug(f"batch size: {len(imgs)}")
        input_ts = [self.transform(image=img)["image"] for img in imgs]
        input_t = torch.stack(input_ts)
        logging.debug(f"input_t: {input_t.shape}")
        output_ts = self.model(input_t)
        activation_fn = torch.nn.__dict__['Sigmoid']()
        output_ts = activation_fn(output_ts)
        labels = list(self.tag2class.keys())
        logging.debug(f"output_ts: {output_ts.shape}")
        #logging.debug(f"output_pb: {output_pb}")
        res = []
        trh = 0.5
        for output_t in output_ts:
            logit = (output_t > trh).long()
            if logit[0] and any([*logit[1:3], *logit[4:]]): 
                output_t[0] = 0
            indices = (output_t > trh).nonzero(as_tuple=True)[0]
            prob = output_t[indices].tolist()
            tag  = [labels[i] for i in indices.tolist()]
            res_dict = dict(zip(
                         list(self.tag2class.keys()),list(output_t.numpy())
                       ))
            logging.debug(f"all results: {res_dict}")
            logging.debug(f"prob: {prob}")
            logging.debug(f"result: {tag}")
            res.append((tag,prob,res_dict))
        result = {k:v for k,v in res_dict.items() if k in ['healthy','leaf rust','stem rust']}
        rem = sum(res_dict.values()) - sum(result.values())
        k,v=max(result.items(), key = lambda k : k[1])
        send_tg_msg(str([v,rem,res_dict,result]))
        return [k,v+rem]

m = ClassifyModel()
m.load()

st.sidebar.title("About")

st.sidebar.info(
    "This application identifies the crop health in the picture.")


st.title('Wheat Rust Identification')

st.write("Upload an image.")
uploaded_file = st.file_uploader("")

if uploaded_file is not None:
    image = PIL.Image.open(uploaded_file).resize((512,512))
    img = np.array(image)
    wheat_type,confidence = m.predict(img)
    st.write(f"I think this is **{wheat_type}**(confidence: **{round(confidence,2)*100}%**)")
    st.image(image, caption='Uploaded Image.', use_column_width=True)
