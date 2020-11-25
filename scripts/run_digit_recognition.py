#!/usr/bin/env python
"""
Real time recognition of digits drawn in the air by hand.

Usage:
  run_digit_recognition.py [--camera_id=CAMERA_ID]
                           [--path_in=FILENAME]
                           [--path_out=FILENAME]
                           [--title=TITLE]
                           [--use_gpu]
  run_digit_recognition.py (-h | --help)

Options:
  --camera_id=CAMERA_ID      Index of the camera to be used as input. Defaults to 0.
  --path_in=FILENAME         Video file to stream from
  --path_out=FILENAME        Video file to stream to
  --title=TITLE              This adds a title to the window display
  --use_gpu                  Use GPU for inference
"""
from docopt import docopt

import realtimenet.display
from realtimenet import camera
from realtimenet import engine
from realtimenet import feature_extractors
from realtimenet.downstream_tasks.digit_recognition import INT2LAB
from realtimenet.downstream_tasks.nn_utils import Pipe, LogisticRegression
from realtimenet.downstream_tasks.postprocess import PostprocessClassificationOutput


if __name__ == "__main__":
    # Parse arguments
    args = docopt(__doc__)
    camera_id = args['--camera_id'] or 0
    path_in = args['--path_in'] or None
    path_out = args['--path_out'] or None
    title = args['--title'] or None
    use_gpu = args['--use_gpu']

    # Load feature extractor
    feature_extractor = feature_extractors.StridedInflatedEfficientNet()
    checkpoint = engine.load_weights('resources/backbone/strided_inflated_efficientnet.ckpt')
    feature_extractor.load_state_dict(checkpoint)
    feature_extractor.eval()

    # Load a logistic regression classifier
    digit_classifier = LogisticRegression(num_in=feature_extractor.feature_dim,
                                          num_out=12)
    checkpoint = engine.load_weights('resources/digit_recognition/efficientnet_logistic_regression.ckpt')
    digit_classifier.load_state_dict(checkpoint)
    digit_classifier.eval()

    # Concatenate feature extractor and met converter
    net = Pipe(feature_extractor, digit_classifier)

    # Create inference engine, video streaming and display instances
    inference_engine = engine.InferenceEngine(net, use_gpu=use_gpu)

    video_source = camera.VideoSource(camera_id=camera_id,
                                      size=inference_engine.expected_frame_size,
                                      filename=path_in)

    video_stream = camera.VideoStream(video_source,
                                      inference_engine.fps)

    postprocessor = [
        PostprocessClassificationOutput(INT2LAB, smoothing=4)
    ]

    display_ops = [
        realtimenet.display.DisplayTopKClassificationOutputs(top_k=1, threshold=0.5),
        realtimenet.display.DisplayDigits(threshold=0.5, duration=2, border_size=50),
    ]
    display_results = realtimenet.display.DisplayResults(title=title, display_ops=display_ops, border_size=50)

    engine.run_inference_engine(inference_engine,
                                video_stream,
                                postprocessor,
                                display_results,
                                path_out)