import requests

token = "<YOUR_TOKEN>"
owner = "<OWNER>"
repo = "<REPO>"
repo_uri = f"https://api.github.com/repos/{owner}/{repo}"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

main_response = requests.get(f"{repo_uri}/commits", headers={**headers, "sha": "main"})
pull_requests_response = requests.get(f"{repo_uri}/pulls", headers=headers)

if 200 not in [pull_requests_response.status_code, main_response.status_code]:
    print("Failed to get your requests")

main_branch = main_response.json()[0]["sha"]

pulls = [
    pull
    for pull in pull_requests_response.json()
    if not pull["draft"] and "SCP" in pull["title"]
]

for pull in pulls:
    status_response = requests.get(f"{repo_uri}/commits/{pull['head']['sha']}/status", headers=headers)
    review_response = requests.get(f"{repo_uri}/pulls/{pull['number']}/reviews", headers=headers)
    pr_response = requests.get(f"{repo_uri}/pulls/{pull['number']}", headers=headers)

    if 200 not in [status_response.status_code, review_response.status_code, pr_response.status_code]:
        print("Failed to get pull requests statuses/reviews")

    statuses = status_response.json()
    reviews = review_response.json()
    pull_request = pr_response.json()
    
    if len(reviews) == 0: reviews = [{"state": "N_REVIEW"}]
    review = reviews[0]
    ci_state = "CI passed" if statuses['state'] == 'success' else "CI failed"
    branch_up_to_date = pull_request['base']['sha'] == main_branch

    # TODO: I need to check all the possible statuses
    mergeable_states = {
        "***********MERGEABLE************": pull_request['mergeable'] and pull_request['mergeable_state'] == "clean" and branch_up_to_date,
        "**MERGEABLE_AND_UP_NOT_TO_DATE**": pull_request['mergeable'] and pull_request['mergeable_state'] == "clean" and not branch_up_to_date,
        "*********NOT_MERGEABLE**********": pull_request['mergeable'] and pull_request['mergeable_state'] == "blocked",
        "*********HAVE_CONFLICTS*********": not pull_request['mergeable'] and pull_request['mergeable_state'] == "dirty",
        "NOT_MERGEABLE_AND_UP_NOT_TO_DATE": pull_request['mergeable'] and pull_request['mergeable_state'] == "behind",
    }
    mergeable = [state for state, value in mergeable_states.items() if value]
    
    template = "#{pr_number}\t| {author}  \t| {pr_state} - {ci_state} - {review_state} - {mergeable}\t| {url}"

    print(template.format(
        pr_number=pull['number'],
        author=pull['user']['login'],
        pr_state=pull['state'],
        ci_state=ci_state,
        review_state=review['state'],
        mergeable=mergeable,
        url=pull['html_url'],
    ))
