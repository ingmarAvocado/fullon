from apify_client import ApifyClient

# uso actor: apidojo/tweet-scraper

APIFY_TOKEN = "apify_api_biOTb5NIcxfTh5o15iasiDC8JMRr6n4e670N"
client = ApifyClient(APIFY_TOKEN)

# Prepara input de actor, aqui busco twits de autor kimmetainen con contenido NFLfi
# ojo al ponerlo en author es como poner un AND es obligatorio
# twitterHandles es como un OR jala esos, más lo que este en la busqueda. hay que validarlo pero me parece asi jala
run_input = {
    "startUrls": [],
    "searchTerms": ['NFLfi',],
    "twitterHandles": [],
    "maxItems": 10,
    "sort": "Top",
    "tweetLanguage": "en",
    "minimumRetweets": 0,
    "author": "kimmetainen",
    "minimumFavorites": 0,
    "minimumReplies": 0,
    "onlyImage": False,
    "onlyQuote": False,
    "onlyTwitterBlue": False,
    "onlyVerifiedUsers": False,
    "onlyVideo": False,
    "start": "2024-01-15",
    "end": "2024-01-30",
    "customMapFunction": "(object) => { return {...object} }",
}


# Run the Actor and wait for it to finish
run = client.actor("61RPP7dywgiy0JPD0").call(run_input=run_input)

# Fetch and print Actor results from the run's dataset (if there are any)
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    #aqui es donde hay que procesar y guardar en nuestra base de datos los twitts relevantes.
    print(item)

# Para que me traiga un twitt que tenga un comentario independientemente de quien venga
# aqui por ejemplo estoy buscando surveillanceparadise
run_input = {
    "customMapFunction": "(object) => { return {...object} }",
    "maxItems": 5,
    "minimumFavorites": 0,
    "minimumReplies": 0,
    "minimumRetweets": 0,
    "onlyImage": False,
    "onlyQuote": False,
    "onlyTwitterBlue": False,
    "onlyVerifiedUsers": False,
    "onlyVideo": False,
    "searchTerms": ["surveillanceparadise"],
    "sort": "Latest",
    "start": "2024-01-15"
}


# Run the Actor and wait for it to finish
run = client.actor("61RPP7dywgiy0JPD0").call(run_input=run_input)

# ahora mejor saquemos la info de todos.
runs = client.actor("61RPP7dywgiy0JPD0").runs()
for run in runs.list().items:
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        print(item)
