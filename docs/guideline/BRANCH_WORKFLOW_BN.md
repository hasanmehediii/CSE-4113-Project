# বাংলায় Branch, Push, Pull ও Merge-এর নিয়ম

আমাদের কাজের মূল নিয়ম: **প্রতিটি কাজ আলাদা branch-এ হবে, সম্পন্ন কাজ আগে `dev`-এ যাবে, তারপর যাচাই করা পরিবর্তন `main`-এ যাবে।** এতে দলের চলমান কাজ একত্র করা যায় এবং `main`-এ স্থিতিশীল code রাখা যায়।

Commit message লেখার নিয়ম জানতে [বাংলা Commit Guide](COMMIT_GUIDE_BN.md) পড়ুন। Command-গুলো repository-এর root folder থেকে চালাবেন। উদাহরণের branch name ও file path নিজের কাজ অনুযায়ী পরিবর্তন করুন।

## ১. সহজ ভাষায় Git-এর শব্দগুলো

| শব্দ | অর্থ |
| --- | --- |
| Branch | মূল code থেকে আলাদা হয়ে নির্দিষ্ট কাজ করার জায়গা |
| Commit | নিজের কম্পিউটারে পরিবর্তনের একটি ধাপ সংরক্ষণ করা |
| Push | নিজের branch-এর commit GitHub-এ পাঠানো |
| Fetch | remote-এর নতুন commit-এর তথ্য আনা; বর্তমান branch-এ merge করে না |
| Pull | remote থেকে নতুন commit এনে নিজের বর্তমান branch-এ যুক্ত করা |
| Merge | এক branch-এর পরিবর্তন অন্য branch-এ একত্র করা |
| Pull Request বা PR | GitHub-এ একটি branch-এর কাজ অন্য branch-এ merge করার review request |
| `origin` | এই repository-এর remote-এর নাম |
| `origin/dev` | সর্বশেষ fetch অনুযায়ী GitHub-এর `dev` branch-এর স্থানীয় reference |

**Push এবং merge আলাদা কাজ।** `feature/auth-token` push করলে code GitHub-এর ওই branch-এ যাবে; `dev` বা `main`-এ নিজে থেকে যাবে না। Pull এবং Pull Request-ও আলাদা: pull দিয়ে নিজের কম্পিউটারের code update করেন, PR দিয়ে merge-এর জন্য review চান।

## ২. কোন Branch কী কাজে ব্যবহার হবে?

| Branch | কাজ | নিয়ম |
| --- | --- | --- |
| `main` | যাচাই করা স্থিতিশীল code রাখা | সরাসরি কাজ বা push নয়; `dev` থেকে reviewed PR merge হবে |
| `dev` | দলের সম্পন্ন কাজ একত্র করা | পরীক্ষিত task branch স্থানীয়ভাবে merge করে `dev` push করবেন |
| Task branch | একটি feature, fix বা নির্দিষ্ট কাজ | সদস্য এখানে কাজ, commit এবং push করবেন |

```text
সর্বশেষ dev
    └── feature/auth-token বা fix/auth-api
            └── commit → push → স্থানীয় dev update → merge → dev push

dev-এর একত্রিত কাজ → পরীক্ষা → PR → review → main-এ merge
```

দৈনন্দিন code পরিবর্তন task branch-এ করুন। আমাদের workflow-তে পরীক্ষিত task branch স্থানীয় `dev`-এ merge করে `dev` push করা যাবে। `main`-এ সরাসরি কাজ বা push করবেন না; সেখানে maintainer reviewed release PR merge করবেন।

## ৩. Branch-এর নাম লেখার নিয়ম

```text
<কাজের-ধরন>/<সংক্ষিপ্ত-বিবরণ>
```

নাম ইংরেজি ছোট হাতের অক্ষরে লিখুন। space-এর বদলে hyphen (`-`) ব্যবহার করুন। একটি branch-এ একটি নির্দিষ্ট কাজ রাখুন।

| কাজ | Prefix | উদাহরণ |
| --- | --- | --- |
| নতুন feature | `feature/` | `feature/auth-token` |
| bug fix | `fix/` | `fix/auth-api` |
| documentation | `docs/` | `docs/setup-guide` |
| code formatting | `style/` | `style/api-formatting` |
| code পুনর্গঠন | `refactor/` | `refactor/auth-service` |
| performance | `perf/` | `perf/user-query` |
| test | `test/` | `test/auth-token` |
| build configuration | `build/` | `build/web-config` |
| CI workflow | `ci/` | `ci/api-tests` |
| maintenance | `chore/` | `chore/update-dependencies` |
| আগের পরিবর্তন ফেরানো | `revert/` | `revert/token-expiry` |

উদাহরণ: branch হবে `feature/auth-token`, আর commit শুরু হবে `(feat): ...` দিয়ে। Issue number থাকলে `fix/42-auth-api`-এর মতো নামও ব্যবহার করতে পারেন।

## ৪. নতুন কাজ শুরু করার সম্পূর্ণ ধাপ

### ধাপ ১: নিজের বর্তমান কাজের অবস্থা দেখুন

```powershell
git status
```

অসম্পূর্ণ পরিবর্তন থাকলে আগে বর্তমান task branch-এ যথাযথ message দিয়ে commit করুন। সাময়িকভাবে সরিয়ে রাখতে চাইলে:

```powershell
git stash push -u -m "unfinished task work"
```

এটি tracked ও untracked file সাময়িকভাবে রাখে; ignored file রাখে না। পরে **মূল task branch-এ ফিরে** `git stash pop` দিয়ে ফিরিয়ে আনবেন। Conflict হলে নিচের conflict-এর নিয়ম অনুসরণ করুন।

### ধাপ ২: সর্বশেষ dev নিন এবং নতুন Branch বানান

```powershell
git fetch origin
git checkout dev
git pull --ff-only origin dev
git checkout -b fix/auth-flow
```

`--ff-only` local ও remote history আলাদা হয়ে গেলে থেমে যায়। তখন জোর করে reset বা push করবেন না; `git status` দেখে maintainer-এর সঙ্গে সমাধান করুন।

**আগে `dev`-এ checkout, তারপর pull করুন।** `git pull origin dev` বর্তমান branch-এ remote `dev`-এর পরিবর্তন আনে; নিজে থেকে `dev`-এ switch করে না। এখানে plain pull-এর বদলে `--ff-only` ব্যবহার করছি, যাতে local `dev` update করার সময়ে অনিচ্ছাকৃত merge না হয়।

`git checkout -b fix/auth-flow` নতুন branch তৈরি করে সেখানে নিয়ে যায়। Branch আগে থেকেই থাকলে শুধু `git checkout fix/auth-flow` চালান। পুরোনো task branch-এ ফিরলে প্রয়োজন অনুযায়ী নিচের ধাপ দিয়ে সর্বশেষ `dev` যুক্ত করুন; শুধু local `dev` pull করলে task branch update হয় না। `git switch` দিয়েও branch বদলানো যায়; এই গাইডে পরিচিত `checkout` command ব্যবহার করা হয়েছে।

Local-এ `dev` না থাকলে, কিন্তু `origin/dev` থাকলে `git checkout dev`-এর জায়গায় চালান:

```powershell
git checkout --track origin/dev
```

Remote-এও `dev` না থাকলে maintainer আগে branch তৈরি করবেন। নতুন task branch সবসময় updated `dev` থেকে তৈরি করুন।

### ধাপ ৩: কাজ করুন, পরীক্ষা করুন, Commit করুন

Feature implement বা bug fix করুন। প্রাসঙ্গিক test, lint বা build চালান এবং প্রয়োজন হলে app চালিয়ে দেখুন। Setup-এর জন্য [README](../../README.md) দেখুন।

```powershell
git status
git diff
git add .
git diff --cached
git commit -m "(fix): correct authentication flow" -m "কী পরিবর্তন হয়েছে: নিজের পরিবর্তনের বিবরণ লিখুন।" -m "কেন পরিবর্তন হয়েছে: সমস্যার কারণ লিখুন।" -m "যাচাই: চালানো পরীক্ষা ও বাস্তব ফল লিখুন।"
```

Repository root থেকে `git add .` চালালে সব non-ignored নতুন, পরিবর্তিত এবং deleted file stage হয়। তাই আগে `git status` ও পরে `git diff --cached` দেখে নিশ্চিত করুন যে সব পরিবর্তন এই কাজের অংশ। অন্য কাজের file থাকলে `git add .`-এর বদলে নির্দিষ্ট path দিয়ে stage করুন। Message-এর উদাহরণ নিজের কাজ অনুযায়ী বদলাবেন। প্রথম `-m` শিরোনাম এবং পরেরগুলো বিস্তারিত body; আরও উদাহরণ [Commit Guide](COMMIT_GUIDE_BN.md)-এ আছে।

### ধাপ ৪: নিজের Branch Push করুন

প্রথমবার:

```powershell
git push -u origin fix/auth-flow
```

`-u` এই local branch-এর সঙ্গে remote branch-এর সম্পর্ক সেট করে। একই branch-এ পরের commit-গুলোর জন্য:

```powershell
git push
```

### ধাপ ৫: সর্বশেষ dev-এ Task Branch Merge করে Push করুন

Task branch-এর কাজ পরীক্ষা ও push করার পরে:

```powershell
git checkout dev
git pull --ff-only origin dev
git merge --no-commit --no-ff fix/auth-flow
```

সাধারণ `git merge fix/auth-flow` দিয়েও merge করা যায়। এখানে `--no-commit --no-ff` দিয়ে merge commit-এর আগে থামানো হচ্ছে, যাতে একত্রিত code পরীক্ষা করে নিজের format-এ বিস্তারিত message দিতে পারেন। Conflict হলে ৬ নম্বর অংশ অনুসরণ করুন। Git `Already up to date` বললে নতুন merge commit লাগবে না। অন্যথায় প্রাসঙ্গিক পরীক্ষা চালিয়ে:

```powershell
git diff --cached
git commit -m "(chore): merge auth flow fix into dev" -m "কী পরিবর্তন হয়েছে: fix/auth-flow-এর কাজ dev-এ যুক্ত করা হয়েছে।" -m "কেন পরিবর্তন হয়েছে: দলের একত্রিত code-এ fix যোগ করার জন্য।" -m "যাচাই: একত্রিত code-এ চালানো পরীক্ষা ও বাস্তব ফল লিখুন।"
git push origin dev
```

Merge-এর আগে আবার pull জরুরি, কারণ আপনার কাজ চলার সময়ে অন্য সদস্য `dev` push করতে পারেন। Merge-এর পরে পরীক্ষা ব্যর্থ হলে push করবেন না; সমস্যা সমাধান করে আবার যাচাই করুন।

### ধাপ ৬: dev Push প্রত্যাখ্যান হলে

Pull ও push-এর মাঝেও অন্য সদস্য `dev` push করতে পারেন। তখন `non-fast-forward` বা `fetch first` error হলে force push করবেন না। নিজের merge commit সংরক্ষিত এবং working tree পরিষ্কার আছে নিশ্চিত করে:

```powershell
git fetch origin
git merge --no-commit --no-ff origin/dev
```

নতুন merge প্রয়োজন হলে conflict সমাধান, পরীক্ষা এবং বিস্তারিতসহ `(chore): ...` merge commit করুন; তারপর `git push origin dev` দিন। `Already up to date` হলে নতুন commit লাগবে না। Remote আবার বদলালে একইভাবে update করুন। এতে অন্যের commit এবং আপনার merge দুটোই রাখা হয়।

### বিকল্প: dev Protected থাকলে PR

Repository-তে `dev`-এর direct push বন্ধ থাকলে local merge push করার বদলে GitHub-এ **Base = `dev`, Compare = আপনার task branch** দিয়ে PR খুলুন। Title-এ `(fix): ...` বা উপযুক্ত type এবং description-এ পরিবর্তন ও পরীক্ষার ফল লিখুন। Reviewer merge করবেন। এই বিকল্প পদ্ধতিতে কাজ করার সিদ্ধান্ত নিলে দলের সবাইকে জানান।

## ৫. কাজ চলার সময়ে dev বদলে গেলে

অন্য সদস্যের কাজ `dev`-এ merge হলে আপনার task branch-এ সেটি আনতে পারেন। আগে working tree পরিষ্কার করুন, তারপর:

```powershell
git checkout fix/auth-flow
git fetch origin
git merge --no-commit --no-ff origin/dev
```

এই command merge commit তৈরির আগে থামে, যাতে পরিবর্তন দেখে দলের format-এ message লিখতে পারেন। Git যদি `Already up to date` বলে, নতুন merge commit লাগবে না। অন্যথায় পরিবর্তন ও প্রাসঙ্গিক test যাচাই করে:

```powershell
git diff --cached
git commit
git push
```

Merge commit-এর message-এর উদাহরণ:

```text
(chore): merge latest dev into auth flow branch

কী পরিবর্তন হয়েছে:
- dev-এর সর্বশেষ পরিবর্তন auth flow branch-এ যুক্ত করা হয়েছে।

কেন পরিবর্তন হয়েছে:
- দলের সর্বশেষ code-এর সঙ্গে কাজটি মিলিয়ে নেওয়ার জন্য।

যাচাই:
- চালানো test এবং বাস্তব ফলাফল এখানে লিখুন।
```

## ৬. Merge Conflict হলে কী করবেন?

দুই branch-এ একই অংশ এমনভাবে বদলালে, যা Git নিজে মেলাতে পারে না, conflict হয়। এতে আপনার কাজ হারিয়ে যায় না; কোন code রাখা হবে তা ঠিক করতে হয়।

১. `git status` দিয়ে conflict থাকা file দেখুন।
২. প্রতিটি file খুলে দুই পাশের পরিবর্তন বুঝুন। File-এ সাধারণত নিচের marker থাকবে:

```text
<<<<<<< HEAD
আপনার বর্তমান branch-এর code
=======
যে branch merge করছেন, সেখান থেকে আসা code
>>>>>>> merged-branch
```

Marker-এর পাশে `origin/dev` বা `fix/auth-flow`-এর মতো আসল branch name থাকতে পারে।

৩. প্রয়োজনীয় code মিলিয়ে final version রাখুন এবং marker-গুলো সরান। শুধু সব file-এ নিজের বা অন্যের version বেছে নেবেন না। বুঝতে না পারলে সংশ্লিষ্ট সদস্যের সাহায্য নিন।
৪. সমাধান করা file stage করে পরীক্ষা করুন, তারপর merge শেষ করুন:

```powershell
git add path/to/resolved-file
git diff --cached
git commit
git push
```

Merge বাতিল করে আগের অবস্থায় ফিরতে চাইলে, merge চলাকালীন:

```powershell
git merge --abort
```

Shared branch-এ force push করবেন না। অন্যের code মুছে দিয়ে conflict সমাধান করবেন না।

## ৭. কাজ dev-এ Merge ও Push হওয়ার পরে

```powershell
git checkout dev
git pull --ff-only origin dev
git checkout -b fix/auth-api
```

এবার নতুন কাজ নতুন branch-এ করুন। পুরোনো merged branch-এ নতুন feature যোগ করবেন না।

## ৮. কখন এবং কীভাবে dev থেকে main-এ যাবে?

আমাদের পরিকল্পনা হলো **শেষবার `main`-এ merge করার পর প্রায় ১০–১৫টি commit জমলে, অথবা একটি বড় feature বা উল্লেখযোগ্য পরিবর্তন সম্পন্ন হলে**, maintainer `dev` থেকে `main`-এ merge করার প্রস্তুতি নেবেন।

**১০–১৫টি commit হলো review করার সময়ের নির্দেশনা; স্বয়ংক্রিয় merge-এর শর্ত নয়।** Squash করলে অনেক task commit একটি commit হয়ে যেতে পারে, তাই সম্পন্ন কাজের পরিমাণও দেখবেন। পরীক্ষা ব্যর্থ হলে বা গুরুত্বপূর্ণ bug থাকলে commit সংখ্যা পূর্ণ হলেও `main`-এ merge হবে না।

Maintainer বা দায়িত্বপ্রাপ্ত release owner-এর ধাপ:

১. `dev`-এর একত্রিত code দিয়ে app-এর গুরুত্বপূর্ণ flow, প্রাসঙ্গিক test ও build যাচাই করুন।
২. প্রয়োজনীয় configuration পরিবর্তন এবং জানা সমস্যা পর্যালোচনা করুন।
৩. GitHub-এ PR খুলুন: **Base = `main`, Compare = `dev`**।
৪. PR-এ অন্তর্ভুক্ত feature, fix, প্রয়োজনীয় setup পরিবর্তন ও যাচাইয়ের ফল লিখুন।
৫. Review এবং প্রযোজ্য check পাস হলে PR merge করুন। কোনো সমস্যা হলে নতুন task branch থেকে fix প্রথমে `dev`-এ আনুন।

PR title বা merge commit-এর শিরোনাম হতে পারে:

```text
(chore): merge verified development changes into main
```

Message-এর body-তেও পরিবর্তন ও যাচাইয়ের সারাংশ রাখুন। `dev` একটি দীর্ঘমেয়াদি shared branch, তাই release PR merge করার পরে সেটি delete করবেন না।

`dev` → `main` PR-এ সাধারণ merge commit পদ্ধতি ব্যবহার করুন, যাতে shared history বজায় থাকে। Release merge-এর পরে maintainer প্রয়োজন হলে GitHub-এ **Base = `dev`, Compare = `main`** দিয়ে synchronization PR খুলে review ও merge করবেন। এতে পরবর্তী কাজ ও release-এর আগে দুই branch-এর history সামঞ্জস্যপূর্ণ থাকে।

## ৯. main নিরাপদ রাখতে Repository Setup

এই document নিয়ম বোঝায়; Git নিজে থেকে এই নিয়ম enforce করবে না। Maintainer-কে GitHub-এর branch protection বা ruleset দিয়ে `main` সুরক্ষিত করতে হবে:

- merge-এর আগে PR ও review approval বাধ্যতামূলক করুন।
- সরাসরি push, force push এবং branch deletion বন্ধ রাখুন।
- `main`-এ merge-এর দায়িত্ব maintainer বা নির্ধারিত release owner-এর কাছে রাখুন।
- CI চালু হলে প্রাসঙ্গিক check পাস করা বাধ্যতামূলক করুন।
- review-এর unresolved আলোচনা merge-এর আগে সমাধান করুন।

`dev`-এ আমাদের local merge ও push workflow চালু রাখতে অনুমোদিত দলের সদস্যদের push access থাকতে হবে। তবে force push ও branch deletion বন্ধ রাখুন। `dev`-এ PR বাধ্যতামূলক করলে উপরের বিকল্প PR workflow ব্যবহার করতে হবে।

## ১০. দ্রুত মনে রাখার নিয়ম

```text
নতুন কাজ: updated dev → নতুন task branch
কাজ সংরক্ষণ: পরিবর্তন → পরীক্ষা → stage → বিস্তারিতসহ commit
GitHub-এ পাঠানো: নিজের branch push
দলের code-এ যোগ: dev checkout → dev pull → task branch merge → পরীক্ষা → dev push
স্থিতিশীল code প্রকাশ: যাচাই করা dev → PR → review → main
```

উদাহরণ: একজন `feature/auth-token`-এ কাজ করবেন, আরেকজন `fix/auth-flow`-তে। দুজনই নিজের branch commit ও push করবেন। এরপর প্রত্যেকে সর্বশেষ `dev` pull করে নিজের task branch merge, একত্রিত code পরীক্ষা এবং `dev` push করবেন। প্রায় ১০–১৫টি commit বা বড় পরিবর্তনের পরে একত্রিত code যাচাই করে maintainer release PR দিয়ে `dev` থেকে `main`-এ merge করবেন।
