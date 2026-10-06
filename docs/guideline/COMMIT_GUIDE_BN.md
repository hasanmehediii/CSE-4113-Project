# বাংলায় Commit Message লেখার নিয়ম

এই প্রজেক্টে প্রত্যেকটি commit message-এ **একটি সংক্ষিপ্ত শিরোনাম এবং তার নিচে বিস্তারিত বিবরণ থাকতে হবে**। এতে অন্য সদস্য বুঝতে পারবেন কী পরিবর্তন হয়েছে, কেন হয়েছে এবং কীভাবে যাচাই করা হয়েছে।

Branch তৈরি, push, pull ও merge করার নিয়ম জানতে [বাংলা Branch ও Git Workflow গাইড](BRANCH_WORKFLOW_BN.md) পড়ুন।

## ১. Commit কী?

Commit হলো আপনার কাজের একটি সংরক্ষিত ধাপ। যেমন, login API-তে ভুল password-এর handling ঠিক করার পর সেই পরিবর্তন একটি commit-এ সংরক্ষণ করবেন। **Commit করলে কাজ শুধু আপনার কম্পিউটারে সংরক্ষিত হয়; GitHub-এ পাঠাতে push করতে হয়।**

একটি commit-এ একটি সম্পর্কিত কাজ রাখুন। একটি feature এবং তার test একসঙ্গে থাকতে পারে, কিন্তু login fix এবং অন্য পৃষ্ঠার design পরিবর্তন আলাদা commit হওয়া উচিত।

## ২. আমাদের বাধ্যতামূলক Message Format

```text
(type): পরিবর্তনের সংক্ষিপ্ত শিরোনাম

কী পরিবর্তন হয়েছে:
- পরিবর্তনের বিবরণ

কেন পরিবর্তন হয়েছে:
- প্রয়োজন বা সমস্যার ব্যাখ্যা

যাচাই:
- কীভাবে পরীক্ষা করেছেন এবং ফলাফল কী
```

নিয়মগুলো হলো:

- প্রথম লাইনে type ছোট হাতের ইংরেজি অক্ষরে, বন্ধনীর মধ্যে থাকবে: `(feat)`, `(fix)`, `(docs)` ইত্যাদি।
- বন্ধনীর পরে colon এবং একটি space থাকবে: `(feat): add login API`।
- শিরোনামের পরে **একটি খালি লাইন**, তারপর বিস্তারিত বিবরণ থাকবে। Markdown-এর `#` দিয়ে heading লেখার প্রয়োজন নেই।
- শিরোনাম সংক্ষিপ্ত ও নির্দিষ্ট রাখুন; সম্ভব হলে ৭২ অক্ষরের মধ্যে রাখুন।
- শিরোনাম ও বিবরণ বাংলা বা ইংরেজিতে লিখতে পারেন; type ও format একই থাকবে।
- বিস্তারিত অংশে কী বদলেছে, কেন বদলেছে এবং যাচাইয়ের ফল লিখুন। পরীক্ষা না করলে সেটি স্পষ্টভাবে লিখুন; না করা পরীক্ষাকে সফল বলবেন না।

## ৩. কোন কাজের জন্য কোন Type?

| Type | কখন ব্যবহার করবেন | শিরোনামের উদাহরণ |
| --- | --- | --- |
| `feat` | নতুন feature বা সুবিধা যোগ করলে | `(feat): add authentication token API` |
| `fix` | bug বা ভুল আচরণ ঠিক করলে | `(fix): reject expired authentication tokens` |
| `docs` | শুধু documentation পরিবর্তন করলে | `(docs): add Bangla setup instructions` |
| `style` | আচরণ না বদলে code formatting, spacing বা indentation ঠিক করলে | `(style): format authentication service` |
| `refactor` | নতুন feature বা bug fix ছাড়াই code-এর গঠন উন্নত করলে | `(refactor): extract token validation helper` |
| `perf` | কাজের ফল একই রেখে গতি বা resource ব্যবহার উন্নত করলে | `(perf): reduce queries in user lookup` |
| `test` | test যোগ বা সংশোধন করলে | `(test): cover invalid login credentials` |
| `build` | build system, packaging বা dependency configuration বদলালে | `(build): update frontend build configuration` |
| `ci` | automated check বা deployment workflow বদলালে | `(ci): run API tests on pull requests` |
| `chore` | অন্য type-এর মধ্যে পড়ে না এমন নিয়মিত maintenance করলে | `(chore): update gitignore entries` |
| `revert` | আগের কোনো পরিবর্তন ফিরিয়ে নিলে | `(revert): undo token expiry change` |

**নতুন UI feature হলে `feat`, ভাঙা UI ঠিক করলে `fix`।** `style` বলতে code formatting বোঝায়; সব design পরিবর্তন বোঝায় না। কাজের উদ্দেশ্য অনুযায়ী type বেছে নিন।

## ৪. সম্পূর্ণ Message-এর উদাহরণ

### নতুন Feature

```text
(feat): add authentication token API

কী পরিবর্তন হয়েছে:
- সফল login-এর পরে token ফেরত দেওয়ার ব্যবস্থা যোগ করা হয়েছে।
- protected API-তে token যাচাই যোগ করা হয়েছে।

কেন পরিবর্তন হয়েছে:
- login করা ব্যবহারকারীকে শনাক্ত করে API access দেওয়ার জন্য।

যাচাই:
- valid credentials দিয়ে login এবং token দিয়ে API access পরীক্ষা করা হয়েছে।
- token ছাড়া request পাঠালে access প্রত্যাখ্যান হচ্ছে।
```

### Bug Fix

```text
(fix): reject expired authentication tokens

কী পরিবর্তন হয়েছে:
- token-এর মেয়াদ শেষ হলে request প্রত্যাখ্যান করা হচ্ছে।

কেন পরিবর্তন হয়েছে:
- আগে মেয়াদ শেষ হওয়া token দিয়েও protected API ব্যবহার করা যাচ্ছিল।

যাচাই:
- valid ও expired token দিয়ে request পরীক্ষা করা হয়েছে।
- expired token-এর ক্ষেত্রে 401 response পাওয়া গেছে।
```

এই উদাহরণগুলোর যাচাইয়ের বিবরণ নিজের বাস্তব ফলাফল অনুযায়ী লিখবেন।

### অন্য সদস্যের Code পরিবর্তন করা প্রয়োজন হলে

কোনো পরিবর্তনের কারণে পুরোনো API client বা configuration আর কাজ না করলে body-তে `BREAKING CHANGE:` লিখে প্রয়োজনীয় পদক্ষেপ জানান।

```text
(feat): require token for profile API

কী পরিবর্তন হয়েছে:
- profile API-তে authentication বাধ্যতামূলক করা হয়েছে।

কেন পরিবর্তন হয়েছে:
- শুধু login করা ব্যবহারকারীকে profile access দেওয়ার জন্য।

BREAKING CHANGE: profile API request-এ এখন Authorization header লাগবে।
Frontend-এর সংশ্লিষ্ট request-গুলোতে token যোগ করতে হবে।

যাচাই:
- token সহ ও token ছাড়া request পরীক্ষা করা হয়েছে।
```

## ৫. কীভাবে বিস্তারিতসহ Commit করবেন?

নিজের task branch-এ থেকে repository-এর root folder থেকে command চালান। আপনার পরিচিত `git add .` ও `git commit -m` পদ্ধতিতে বিস্তারিতসহ commit করা যায়:

```powershell
git status
git diff
git add .
git diff --cached
git commit -m "(fix): correct authentication flow" -m "কী পরিবর্তন হয়েছে: নিজের পরিবর্তনের বিবরণ লিখুন।" -m "কেন পরিবর্তন হয়েছে: সমস্যার কারণ লিখুন।" -m "যাচাই: চালানো পরীক্ষা ও বাস্তব ফল লিখুন।"
```

Root থেকে `git add .` দিলে সব non-ignored নতুন, পরিবর্তিত এবং deleted file stage হয়। সব পরিবর্তন একই কাজের অংশ কিনা দেখে নিন। অন্য কাজের file থাকলে নিচের মতো নির্দিষ্ট file stage করুন। উদাহরণের message নিজের কাজ অনুযায়ী বদলে নিন।

Editor-এ message লিখতে চাইলে:

```powershell
git status
git diff
git add docs/guideline/COMMIT_GUIDE_BN.md
git diff --cached
git commit
```

`git add` commit-এর জন্য file নির্বাচন করে। `git diff --cached` দিয়ে নির্বাচিত পরিবর্তন দেখবেন। `git commit` চালালে Git-এর configured editor খুলবে। সেখানে প্রথম লাইনে শিরোনাম, একটি খালি লাইন এবং বিস্তারিত বিবরণ লিখে save ও close করুন।

Editor ব্যবহার না করতে চাইলে একাধিক `-m` দিয়ে লিখতে পারেন:

```powershell
git commit -m "(docs): add Bangla commit guide" -m "কী পরিবর্তন হয়েছে: commit type, message format এবং উদাহরণ যোগ করা হয়েছে।" -m "কেন পরিবর্তন হয়েছে: দলের সবাইকে একই নিয়মে commit করতে সাহায্য করার জন্য।" -m "যাচাই: Markdown-এর link ও command example পর্যালোচনা করা হয়েছে।"
```

প্রথম `-m` শিরোনাম এবং পরের `-m`-গুলো আলাদা paragraph হবে। শুধু `git commit -m "(feat): add login API"` চালালে বিস্তারিত থাকবে না, তাই সেটি আমাদের নিয়ম অনুযায়ী অসম্পূর্ণ।

## ৬. ভালো ও অসম্পূর্ণ Message

| অসম্পূর্ণ বা অস্পষ্ট শিরোনাম | ভালো শিরোনাম |
| --- | --- |
| `done` | `(feat): add user registration API` |
| `fixed` | `(fix): handle missing login password` |
| `update` | `(docs): explain local API setup` |
| `feat: add login` | `(feat): add login endpoint` |
| `(feature): add login` | `(feat): add login endpoint` |

ডান পাশের শিরোনামগুলোর পরেও বিস্তারিত body লিখতে হবে। **Commit type হলো `feat`, কিন্তু নতুন feature-এর branch prefix হলো `feature/`**, যেমন `feature/auth-token`।

## ৭. Commit করার আগে ছোট Checklist

- আমি নিজের task branch-এ আছি।
- পরিবর্তন দেখে শুধু এই কাজের প্রয়োজনীয় file stage করেছি।
- message-এ সঠিক `(type): শিরোনাম`, খালি লাইন ও বিস্তারিত আছে।
- প্রযোজ্য পরীক্ষা করেছি এবং বাস্তব ফল লিখেছি।
- password, token, `.env`, `node_modules` বা generated build file ভুল করে stage করিনি।

PR-এর title এবং হাতে লেখা merge বা squash commit message-এও একই format ব্যবহার করুন। Merge বা squash message-এর body-তে সংযুক্ত কাজ এবং যাচাইয়ের সারাংশ লিখুন।
