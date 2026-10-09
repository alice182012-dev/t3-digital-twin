---
title: "Ideas to optimize your planning poker sessions"
source: "https://www.atlassian.com/blog/developers/planning-poker-sane-healthy"
author:
  - "[[Heather Krebsbach]]"
published: 2016-06-20
created: 2026-10-10
description: "An agile team's estimation accuracy actually tends to degrade over time. But the good news is that there are ways to reverse this trend."
tags:
  - "clippings"
---
*This is a guest post by Vitalii Zurian, a software engineer and the creator of a series of agile add-ons for Jira Cloud, including the #1 paid add-on, [Planning Poker](https://marketplace.atlassian.com/plugins/agile.estimation.3.0_private/cloud/overview). Vitalli blogs at [agilevalues.com](https://agile-values.com/).*

As your team matures and becomes more experienced, you’d think your [estimates and planning poker sessions](https://www.atlassian.com/agile/estimation) would improve as well. Seems only natural, right? But that’s not what usually happens. In reality, an agile team’s estimation accuracy actually tends to degrade over time.

That’s a painful truth. But the good news is that there are ways to reverse this trend and get your estimations back on track.

## Pinpointing the problems

If we charted a typical team’s estimation accuracy over time, we would see accuracy degradation not as a trend, but rather as a series of peaks and troughs. In other words, the accuracy loss happens periodically. What matters most is your team’s ability to recognize when your accuracy is slipping, and recover from it.

To help understand what facilitates fast recovery, let’s break down the patterns and psychology that cause this problem in the first place.

### Procrastination

Later, later, later. Let’s discuss it later. Let’s estimate later. Let’s clarify later. Let’s define requirements later. Because doing it now is inconvenient.

Even teams experienced enough to know that good estimation requires good information still fall into this trap. Don’t get me wrong: a “let’s figure that out later” attitude isn’t bad when you’re a lean startup working on MVPs. But procrastination is definitely a no-go when it comes to clarifying user stories and requirements.

### False assumptions

As the team’s experience increases, the product’s complexity often does as well. This leads to making false assumptions during the planning poker sessions. The reason is simple. Because of your experience, you have excellent knowledge of your product and your field, and use your past experience to make estimates. Which makes sense, until a different product is concerned. Or the product you’re an expert in changes fundamentally. Oftentimes we, as experts, mistakenly use our past experience to predict the future of something not closely related.

Being more specific, let’s say a team has spent over a year working with a basic online newspaper. This team successfully achieved stable velocity and decent predictability. Everyone feels awesome. Then this team starts working on a new project: the newspaper’s mobile app. Unconsciously, most of the people will be too optimistic in their estimations because it just “feels right”. Like, I am a mature engineer, I know what I am doing. Or, implementing that feature in the web-based newspaper was 13 point, so of course it’s a 13 to implement it in the mobile app. (I think you know how this story ends…)

> ### We must approach new projects with a “blank” mind when it comes to estimating stories.

### Extreme votes and the unwillingness to speak

This is a common pitfall. Picture the following example:

A new engineer joins a mature team. This new member is an expert, so expectations are high, which results in some deviation of estimates during the planning poker session. The new engineer might shy away from putting high estimates on stories so as not to jeopardize their image as an expert. This can result in the team missing out on “gotchas” or other critical input.

Here’s another common scenario. A team member has some important observations about a user story but decides not to speak. This is totally understandable. Being in the minority and speaking up requires stepping out of one’s comfort zone. Other times when you are in the minority, you might have a false assumption that the other people know something you don’t, so you silently decide to agree with them.

### Loss of focus

Remember those good old days when the planning poker session used to be fun? Yeah, back then when they were actually facilitated by a really engaged person?

Don’t worry if you used to be that really engaged person – there is nothing wrong with you. It’s just that when something transitions from a new thing to a routine, it becomes a bit less enjoyable. In fact, most people stop giving it much attention and just “go through the motions”.

You know the person who always brings a laptop to the meeting room and furiously types when everyone is supposed to be brainstorming a story? It’s not totally their fault. It’s also the meeting facilitator who failed to make the meeting engaging and enforce the team’s “laptops closed” agreement.

By now, you’re probably pretty depressed about planning poker. But don’t give up. It’s possible to reinvigorate this grand tradition by bringing some fresh ideas.*Download a high-res PDF [here](https://s3-eu-west-1.amazonaws.com/agile-values/estimate_better_5_steps.pdf).*

## How to do planning poker at full power again

While reading my analysis of the psychological side of the game, you probably came up with some ideas. Let me help you a little bit more by adding some practical tips.

### Bring in a reference story

As silly as it sounds, experienced teams often forget to refer to the reference. It happens due to the false assumptions mentioned above.

Start planning poker sessions by reviewing the reference story to help your team calibrate their estimates. It helps to choose a new story to use as a reference every few months so it’s always fresh in the memory of engineers, making it easy to compare it to whatever task you’re estimating.

### Stop estimating when tired

It sounds obvious. Yet so many people ignore this simple rule. Do not estimate when you are getting tired.

There is always a desire to finish off the planning backlog completely, even if it means longer planning poker sessions. I know. I’ve been there. I especially remember situations when the team had already estimated 15 stories during 1 hour, but there were still 5 more to go.

Running long to estimate those last few stories pushes everyone to their limits. At that point, planning poker stops being fun and becomes a challenge. And a challenge isn’t what you’re aiming for here. Save “challenge” for when you’re actually implementing the stories.

### Follow-up and calibrate

Following up on something is as important in the estimating ceremony as it is in the world of professional development. Yet not many teams do it.

The process is simple. After the sprint, compare the initially estimated value against the actual value, which could be calculated given the team’s velocity.

**Here’s a sample calculation**:

Imagine we have a 10-day sprint duration and the velocity of the team is 20 (points per sprint). Let’s calculate the team’s average velocity (AV) per iteration unit (story points per day)

![Screen Shot 2016-06-16 at 1.37.43 PM](https://atlassianblog.wpengine.com/wp-content/uploads/Screen-Shot-2016-06-16-at-1.37.43-PM.png)

Say, we have a story estimated for 3 story points. Here’s the prediction formula for the number of days the story could potentially take:

![Screen Shot 2016-06-16 at 1.37.51 PM](https://atlassianblog.wpengine.com/wp-content/uploads/Screen-Shot-2016-06-16-at-1.37.51-PM.png)

We could expect it to be delivered in roughly 1.5 days. Now let’s say the story actually took 3 days to implement. Calculating the **actual story complexity** (ASC) for this story is easy by reversing the latter formula and replacing **estimation** with the unknown variable:

![Screen Shot 2016-06-16 at 1.38.03 PM](https://atlassianblog.wpengine.com/wp-content/uploads/Screen-Shot-2016-06-16-at-1.38.03-PM.png)

An important step is to calibrate the actual story complexity (ASC) by rounding it to the closest Fibonacci number. In our case, **in the sequence part between 5 and 8, current ASC is closer to the 5.** This brings us to the conclusion, that the story was underestimated and it should have been estimated as 5 story points instead of 3.

This way, the team will get some really valuable feedback about its accuracy. From there, it’s best to analyze the discrepancy in estimates, share it with the team, iterate, and move on.

## Final thoughts

While I’ve provided you quite a few tips here, you don’t have to apply all of them at once. Try to pick one that you think can be achieved easily in your specific environment, apply it and observe the improved results. This will motivate you and your team to carry on. Happy estimating!

---

Have any other tips or opinions to share? Let Vitalii know in the comments. And, visit the Atlassian Marketplace to peruse [Vitalii’s add-ons](https://marketplace.atlassian.com/vendors/1211528) and see other great contributions from our vendors.

[Visit the Marketplace](https://marketplace.atlassian.com/)