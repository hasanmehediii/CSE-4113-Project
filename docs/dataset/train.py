import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

DATA_PATH = 'drainage_complaints_bn.csv'
MODEL_PATH = 'complaint_classifier.joblib'
VECTORIZER_PATH = 'tfidf_vectorizer.joblib'


def load_data(path):
    df = pd.read_csv(path, encoding='utf-8-sig')
    return df['text_bn'], df['category']


def build_vectorizer():
    return TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(2, 4),
        max_features=5000,
        sublinear_tf=True,
    )


def train(X_train, y_train, vectorizer):
    X_train_vec = vectorizer.fit_transform(X_train)
    model = LogisticRegression(
        max_iter=1000,
        C=5.0,
        class_weight='balanced',
    )
    model.fit(X_train_vec, y_train)
    return model


def evaluate(model, vectorizer, X_test, y_test):
    X_test_vec = vectorizer.transform(X_test)
    y_pred = model.predict(X_test_vec)
    print(classification_report(y_test, y_pred))
    return y_pred


def plot_confusion_matrix(y_test, y_pred, labels, filename):
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()


def run_cross_validation(X, y, vectorizer_builder, k=5):
    X_vec = vectorizer_builder().fit_transform(X)
    model = LogisticRegression(max_iter=1000, C=5.0, class_weight='balanced')
    scores = cross_val_score(model, X_vec, y, cv=k, scoring='f1_macro')
    print(f'{k}-Fold CV F1-macro scores: {scores}')
    print(f'Mean F1-macro: {scores.mean():.4f} (+/- {scores.std():.4f})')
    return scores


def predict_new(text, model, vectorizer):
    vec = vectorizer.transform([text])
    pred = model.predict(vec)[0]
    proba = model.predict_proba(vec)[0]
    classes = model.classes_
    prob_dict = dict(zip(classes, proba))
    return pred, prob_dict


def main():
    X, y = load_data(DATA_PATH)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    vectorizer = build_vectorizer()
    model = train(X_train, y_train, vectorizer)

    print('--- Test Set Evaluation ---')
    y_pred = evaluate(model, vectorizer, X_test, y_test)

    labels = sorted(y.unique())
    plot_confusion_matrix(y_test, y_pred, labels, 'confusion_matrix.png')

    print('\n--- 5-Fold Cross Validation (on full dataset) ---')
    run_cross_validation(X, y, build_vectorizer, k=5)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    print(f'\nSaved model to {MODEL_PATH}')
    print(f'Saved vectorizer to {VECTORIZER_PATH}')

    print('\n--- Sample Predictions ---')
    samples = [
        'মিরপুরে ড্রেন বন্ধ হয়ে পানি জমে আছে',
        'রাস্তায় ম্যানহোলের ঢাকনা খোলা, বিপজ্জনক অবস্থা',
        'প্রতি বর্ষায় এই এলাকায় জলাবদ্ধতা হয়',
    ]
    for text in samples:
        pred, proba = predict_new(text, model, vectorizer)
        top_prob = proba[pred]
        print(f'Text: {text}')
        print(f'  -> Predicted: {pred} (confidence: {top_prob:.2f})')


if __name__ == '__main__':
    main()