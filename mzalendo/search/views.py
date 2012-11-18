import re

from django.http import HttpResponse
from django.shortcuts  import render_to_response, get_object_or_404, redirect
from django.template   import RequestContext
from django.utils import simplejson
import datetime
from operator import itemgetter

# from mzalendo.helpers import geocode

from core import models

from haystack.query import SearchQuerySet
from mzalendo.models import models as hansard_models

# def location_search(request):
#     
#     loc = request.GET.get('loc', '')
# 
#     results = geocode.find(loc) if loc else []
#     
#     # If there is one result find that matching areas for it
#     if len(results) == 1:
#         mapit_areas = geocode.coord_to_areas( results[0]['lat'], results[0]['lng'] )
#         areas = [ models.Place.objects.get(mapit_id=area['mapit_id']) for area in mapit_areas.values() ]
#     else:
#         areas = None
#         
#     return render_to_response(
#         'search/location.html',
#         {
#             'loc': loc,
#             'results': results,
#             'areas': areas,
#         },
#         context_instance = RequestContext( request ),        
#     )


def autocomplete(request):
    """Return autocomple JSON results"""
    
    term = request.GET.get('term','').strip()
    response_data = []

    if len(term):

        # Does not work - probably because the FLAG_PARTIAL is not set on Xapian
        # (trying to set it in settings.py as documented appears to have no effect)
        # sqs = SearchQuerySet().autocomplete(name_auto=term)

        # Split the search term up into little bits
        terms = re.split(r'\s+', term)

        # Build up a query based on the bits
        sqs = SearchQuerySet()        
        for bit in terms:
            # print "Adding '%s' to the '%s' query" % (bit,term)
            sqs = sqs.filter_and(
                name_auto__startswith = sqs.query.clean( bit )
            )

        # collate the results into json for the autocomplete js
        for result in sqs.all()[0:10]:
            response_data.append({
            	'url':   result.object.get_absolute_url(),
            	'label': result.object.name,
            })
    
    # send back the results as JSON
    return HttpResponse(
        simplejson.dumps(response_data),
        mimetype='application/json'
    )
  

stopwords = ["'tis", "'t was", "a", "able","about", "across", "after", 
             "ain't","all", "almost", "also", "am", "among", "an", "and",   
            "any", "are", "aren't", "as", "at", "be", "because", "been", "but",  
            "by", "can", "can't", "cannot", "could", "could've", "couldn't", 
            "dear", "did", "didn't", "do", "does", "doesn't", "don't", "either", 
            "else", "ever", "every", "for", "from", "get", "got", "had", "has", "hasn't",
            "have", "he", "he'd", "he'll", "he's", "her", "hers", "him", "his", "how", "how'd",
            "how'll", "how's", "however", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into",
            "is", "isn't", "it", "it's", "its", "just", "least", "let", "like", "likely", "may", "me",
            "might", "might've", "mightn't", "most", "must", "must've", "mustn't", "my", "neither",
            "no", "nor", "not", "of", "off", "often", "on", "only", "or", "other", "our", "own", "rather",
            "said", "say", "says", "shan't", "she", "she'd", "she'll", "she's", "should", "should've", 
            "shouldn't", "since", "so", "some", "than", "that", "that'll", "that's", "the", "their", "them", 
            "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "tis",
            "to", "too", "twas", "us", "wants", "was", "wasn't", "we", "we'd", "we'll", "we're", "were", "weren't", "what",
            "what'd", "what's", "when", "when", "when'd", "when'll", "when's", "where", "where'd", "where'll", "where's",
            "which", "while", "who", "who'd", "who'll", "who's", "whom", "why", "why'd", "why'll", 
            "why's", "will", "with", "won't", "would", "would've", "wouldn't", "yet", "you", "you'd",
            "you'll", "you're", "you've", "your" ]

def tagcloud(request):
    """ Return tag cloud JSON results"""
    # Build a query based on duration default is 1 month
    cutoff = datetime.date.today() - datetime.timedelta(weeks=1)
    sqs  = SearchQuerySet().models(hansard_models.Entry).filter(sitting__start_date>=cuttoff)
    cloudlist =[]
    try:
        # Generate tag cloud from content of returned entries
        words = {}
        for entry in sqs.all():
            text = entry.object.content
    
            for x in text.lower().split():
                cleanx = x.replace(',','').replace('.','').replace('"','').strip()
                if not cleanx in stopwords:
                    words[cleanx] = 1 + words.get(cleanx, 0)

        for word in words:
            cloudlist.append({"text":word , "weight": words.get(word), "link":"/search/hansard/?q=%s" % word })

        sortedlist = sorted(cloudlist, key=itemgetter('weight'))[:10]
    except:
        sortedlist =[]

    # return results
    return HttpResponse(
        simplejson.dumps(sortedlist),
        mimetype='application/json'
    )


