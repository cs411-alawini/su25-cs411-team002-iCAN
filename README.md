# team002-iCAN
This is a template for CS411 project repository. Please make sure that your title follows the convention: [TeamID]-[YourTeamName]. All TeamIDs should have a three digit coding (i.e. if you are team 20, you should have `team020` as your ID.). You should also make sure that your url for this repository is [sp25-cs411-team000-teamname.git] so TAs can correctly clone your repository and keep them up-to-date.

Once you setup your project, please remember to submit your team formation to the team form.

## Permission
You should make sure you allow TAs to access your repository. You can add TA(s) as a collaborator to your repository.

## Preparing for your release
Eash submission should be in its own [release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases). Release are specific freezes to your repository. You should submit your commit hash on canvas or google sheet. When tagging your stage, please use the tag `stage.x` where x is the number to represent the stage.

## Keeping things up-to-date
You should make sure you keep your project root files up-to-date. Information for each file/folders are explained.

## Code Contribution
Individual code contribution will be used to evaluate individual contribution to the project.

## Contributing to the repo
Always start by syncing with the main branch:
git checkout main

Pull latest changes from Github:
git pull origin main

Now, your local main branch is up-to-date with the one on github. From here, start a new branch or update an existing one.

To start a new feature branch: 
git checkout -b <branch-name>

To update an existing feature branch:
git checkout <your-feature-branch>
git merge main
