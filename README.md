# Gaspard & Co Real Estate website

The website for Gaspard & Co Real Estate, hosted on Netlify at gaspardandcorealestate.com.

## How to update the site

**Easiest: ask Claude.** Send the new bio, review or change in chat. Claude edits the files here and the live site updates on its own.

**Yourself: Pages CMS.** Go to [app.pagescms.org](https://app.pagescms.org), sign in with GitHub, and open `gaspard-site`. You'll see:

- **Agents**: one form per agent. Add a bio (blank line between paragraphs), add reviews word for word, add links to Zillow or Google reviews, change a phone or email, or tick "Hide this agent."
- **Teams**: team names, group photos and captions.
- **Gaspard Team ad page**: the four reviews, rating line and links on the ad landing page.
- **Company info**: office details, home page wording, which agents show on the home page, and the home search (IDX) code.

Press **Save**. Netlify rebuilds the site in about a minute. Every change is kept in GitHub's history, so anything can be undone.

Only use real reviews, word for word, with the client's permission.

## Adding a new agent

In Pages CMS, open **Agents** and choose **Add an entry**. Upload a headshot (black-and-white on a white background matches the rest of the site; Claude can prepare one from any photo). The agent appears on the agents page in alphabetical order by last name.

## Home search (IDX)

When the Flexmls IDX account for ROAM MLS is ready, paste the embed code Flexmls provides into **Company info → Home search (IDX) code**. A "Search" link then appears in the menu and the Search page shows listings.

## Forms

The forms on the Gaspard Team page (contact and home value) use Netlify Forms. Set notifications in Netlify under **Site configuration → Forms → Form notifications** to email admin@gaspardandcorealestate.com.

## Pages

| Address | Page |
| --- | --- |
| `/` | Home |
| `/agents/` | All agents A–Z, then the teams |
| `/agents/first-last/` | Each agent's page |
| `/teams/gaspard-team/`, `/teams/wattam-five-star-team/` | Team pages |
| `/gaspard-team/` | Gaspard Team ad landing page |
| `/about/` | About and contact |
| `/search/` | Home search (coming soon until IDX is added) |
| `/thanks/` | Shown after a form is sent |

## For developers

`build.py` turns the files in `content/` into the finished site in `dist/`, using only Python's standard library. Netlify runs `python3 build.py` (see `netlify.toml`). `python3 build.py --preview` makes a flat preview with photos built in.
