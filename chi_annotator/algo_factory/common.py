#! /usr/bin/env python
# -*- coding: utf8 -*-

from chi_annotator.algo_factory.utils import ordered
from chi_annotator.algo_factory.utils import lazyproperty

import os
import json
import io
import datetime

import chi_annotator


class InvalidProjectError(Exception):
    """Raised when a model failed to load.

    Attributes:
        message -- explanation of why the model is invalid
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class MissingArgumentError(Exception):
    """Raised when a args missing.

    Attributes:
        message -- explanation of why the model is invalid
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class Metadata(object):
    """Captures all information about a model to load and prepare it."""

    @staticmethod
    def load(model_dir):
        # type: (Text) -> 'Metadata'
        """Loads the metadata from a models directory."""
        try:
            metadata_file = os.path.join(model_dir, 'metadata.json')
            with io.open(metadata_file, encoding="utf-8") as f:
                data = json.loads(f.read())
            return Metadata(data, model_dir)
        except Exception as e:
            abspath = os.path.abspath(os.path.join(model_dir, 'metadata.json'))
            raise InvalidProjectError("Failed to load model metadata "
                                      "from '{}'. {}".format(abspath, e))

    def __init__(self, metadata, model_dir):
        # type: (Dict[Text, Any], Optional[Text]) -> None

        self.metadata = metadata
        self.model_dir = model_dir

    def get(self, property_name, default=None):
        return self.metadata.get(property_name, default)

    @property
    def language(self):
        # type: () -> Optional[Text]
        """Language of the underlying model"""

        return self.get('language')

    @property
    def pipeline(self):
        # type: () -> List[Text]
        """Names of the processing pipeline elements."""

        return self.get('pipeline', [])

    def persist(self, model_dir):
        # type: (Text) -> None
        """Persists the metadata of a model to a given directory."""

        metadata = self.metadata.copy()

        metadata.update({
            "trained_at": datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),
            "nlu_version": chi_annotator.algo_factory.__version__,
        })

        with io.open(os.path.join(model_dir, 'metadata.json'), 'w') as f:
            f.write(str(json.dumps(metadata, indent=4)))


class Message(object):
    """basic moudule for data"""
    def __init__(self, text, data=None, output_properties=None, time=None):
        self.text = text
        self.time = time
        self.data = data if data else {}
        self.output_properties = output_properties if output_properties else set()

    def set(self, prop, info, add_to_output=False):
        self.data[prop] = info
        if add_to_output:
            self.output_properties.add(prop)

    def update(self, prop, info, add_to_output=False):
        """更新message的参数，如果message对应的key已经存在，那么在key->value后面调用extend"""
        if prop in self.data:
            if type(info) != type(self.data[prop]):
                return False
            if isinstance(self.data[prop], list):
                self.data[prop].extend(info)
            elif isinstance(self.data[prop], dict) or isinstance(self.data[prop], set):
                self.data[prop].update(info)
            else:
                return False
        else:
            self.data[prop] = info
        if add_to_output:
            self.output_properties.add(prop)
        return True

    def get(self, prop, default=None):
        return self.data.get(prop, default)

    def as_dict(self, only_output_properties=False):
        if only_output_properties:
            d = {key: value for key, value in list(self.data.items()) if key in self.output_properties}
        else:
            d = self.data
        return dict(d, text=self.text)

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        else:
            return (other.text, ordered(other.data)) == (self.text, ordered(self.data))

    def __hash__(self):
        return hash((self.text, str(ordered(self.data))))


class TrainingData(object):
    """Holds loaded intent and entity training data."""

    # Validation will ensure and warn if these lower limits are not met
    MIN_EXAMPLES_PER_CLASSIFY = 2
    MIN_EXAMPLES_PER_ENTITY = 2

    def __init__(self, training_examples=None):
        # type: (Optional[List[Message]], Optional[Dict[Text, Text]]) -> None
        self.training_examples = training_examples
        self.validate()

    @lazyproperty
    def classify_examples(self):
        # type: () -> List[Message]
        return [e for e in self.training_examples if e.get("classify") is not None]

    @lazyproperty
    def entity_examples(self):
        # type: () -> List[Message]
        return [e for e in self.training_examples if e.get("entities") is not None]

    @lazyproperty
    def num_entity_examples(self):
        # type: () -> int
        """Returns the number of proper entity training examples (containing at least one annotated entity)."""

        return len([e for e in self.training_examples if len(e.get("entities", [])) > 0])

    @lazyproperty
    def num_intent_examples(self):
        # type: () -> int
        """Returns the number of intent examples."""
        return len(self.intent_examples)

    def example_iter(self):
        """
        iterator for all samples
        :return: message
        """
        for example in self.training_examples:
            yield example

    def as_json(self, **kwargs):
        # type: (**Any) -> str
        """Represent this set of training examples as json adding the passed meta information."""
        pass

    def as_markdown(self, **kwargs):
        # type: (**Any) -> str
        """Represent this set of training examples as markdown adding the passed meta information."""
        pass

    def persist(self, dir_name):
        # type: (Text) -> Dict[Text, Any]
        """Persists this training data to disk and returns necessary information to load it again."""
        pass

    def sorted_entity_examples(self):
        # type: () -> List[Message]
        """Sorts the entity examples by the annotated entity."""

        return sorted([entity for ex in self.entity_examples for entity in ex.get("entities")],
                      key=lambda e: e["entity"])

    def sorted_classify_examples(self):
        # type: () -> List[Message]
        """Sorts the classify examples by the name of the intent."""

        return sorted(self.classify_examples, key=lambda e: e.get("classify"))

    def validate(self):
        # type: () -> None
        """Ensures that the loaded training data is valid, e.g. has a minimum of certain training examples."""
        pass
