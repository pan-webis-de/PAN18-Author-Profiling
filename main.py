#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# File : main.py
# Description : Main program for execution.
# Auteur : Nils Schaetti <nils.schaetti@unine.ch>
# Date : 01.02.2017 17:59:05
# Lieu : Neuchâtel, Suisse
#
# This file is part of the PAN18 author profiling challenge code.
# The PAN18 author profiling challenge code is a set of free software:
# you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Foobar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#

# Imports
import os
import torch
import dataset
from torch.autograd import Variable
from tools import settings, functions


################################################
# MAIN
################################################

# Argument parser
args = functions.argument_parser_execution()

# Image augmentation and normalization
image_transform = functions.image_transformer('val')

# Counters
total_images_success = 0.0
total_tweets_success = 0.0
total_both_success = 0.0
total = 0.0

# For each language
for lang in ['en', 'es', 'ar']:
    # Load models and voc
    image_model, tweet_model, tweet_voc = functions.load_models(
        model_type=args.image_model,
        n_gram=args.n_gram,
        lang=lang,
        cuda=args.cuda
    )

    # Counters
    images_success = 0.0
    tweets_success = 0.0
    both_success = 0.0
    count = 0

    # Make to output directory
    output_dir = os.path.join(args.output_dir, lang)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    # end

    # Transformer
    text_transform = functions.tweet_transformer(lang, args.n_gram, voc=tweet_voc)

    # Author profiling data set
    profiling_dataset = dataset.TIRAAuthorProfilingDataset(root=args.input_dataset, text_transform=text_transform,
                                                           lang=lang, image_transform=image_transform,
                                                           filter_robot=True)
    pan18loader = torch.utils.data.DataLoader(profiling_dataset, batch_size=1, shuffle=True)

    # For the data set
    for data in pan18loader:
        # Images, tweets and labels
        tweets, images, labels = data

        # Variable and CUDA
        images, tweets, labels = Variable(images), Variable(tweets), Variable(labels)
        if args.cuda:
            images, tweets, labels = images.cuda(), tweets.cuda(), labels.cuda()
        # end if

        # Tweets batch size
        tweets_batch_size = tweets.size(1)

        # Remove images and tweet dimension
        tweets = tweets.view(-1, settings.min_length)
        images = images.view(-1, 3, settings.image_size, settings.image_size)

        # Compute prob. for tweets and images
        images_probs = image_model(images)
        tweets_probs = tweet_model(tweets)

        # Resize to images and tweet dimension and transpose
        tweets_probs = tweets_probs.view(-1, tweets_batch_size, 2)
        images_probs = images_probs.view(-1, 10, 2)

        # Take the max as predicted
        _, images_prediction = torch.max(torch.mean(images_probs, 1), 1)
        _, tweets_prediction = torch.max(torch.mean(tweets_probs, 1), 1)

        # Add to correctly classified profiles
        images_success += int((images_prediction == labels).sum())
        tweets_success += int((tweets_prediction == labels).sum())
        both_success += int((tweets_prediction == labels).sum())

        # Add to total
        count += labels.size(0)

        # Save result
        author_id = profiling_dataset.last_idxs[-1]
        functions.save_result(
            output_dir,
            author_id,
            lang,
            tweets_prediction[-1],
            images_prediction[-1],
            tweets_prediction[-1]
        )
    # end for

    # Total success
    total_images_success += images_success
    total_tweets_success += tweets_success
    total_both_success += both_success
    total += count

    # Accuracies
    images_accuracy = images_success / count * 100.0
    tweets_accuracy = tweets_success / count * 100.0
    both_accuracy = both_success / count * 100.0

    # Print language accuracy
    print(u"Lang {}, Images accuracy {}, Tweets accuracy {}, Both accuracy {}".format(
        lang,
        images_accuracy,
        tweets_accuracy,
        both_accuracy)
    )
# end for

# Accuracies
total_images_accuracy = total_images_success / total * 100.0
total_tweets_accuracy = total_tweets_success / total * 100.0
total_both_accuracy = total_both_success / total * 100.0

# Print total accuracy
print(u"Images accuracy {}, Tweets accuracy {}, Both accuracy {}".format(
    total_images_accuracy,
    total_tweets_accuracy,
    total_both_accuracy)
)
