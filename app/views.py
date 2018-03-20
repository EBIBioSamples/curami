# from .models import User, get_todays_recent_posts, get_pairs, get_samples, get_last_coexistance_update, get_last_autocluster_update, get_last_lexical_update, get_last_values_update, get_num_samples_processed
from .models import *
from .reccomendation import *
from flask import Flask, request, session, redirect, url_for, render_template, flash
import sys

app = Flask(__name__)

@app.route('/')
def index():
    username = session.get('username')
    num_pairs = get_pairs()
    num_samples = get_samples()

    last_coexistance_update = get_last_coexistance_update()
    coexistance_last_update_date = last_coexistance_update[0]
    coexistance_last_update_time = last_coexistance_update[1]

    last_autocluster_update = get_last_autocluster_update()
    autocluster_last_update_date = last_autocluster_update[0]
    autocluster_last_update_time = last_autocluster_update[1]

    last_lexical_update = get_last_lexical_update()
    lexical_last_update_date = last_lexical_update[0]
    lexical_last_update_time = last_lexical_update[1]

    last_values_update = get_last_values_update()
    values_last_update_date = last_values_update[0]
    values_last_update_time = last_values_update[1]


    num_samples_processed = get_num_samples_processed()
    lexical_num_processed = num_samples_processed[0]
    autocluster_num_processed = num_samples_processed[1]
    values_num_processed = num_samples_processed[2]
    coexistance_num_processed = num_samples_processed[3]


    return render_template('index.html',

        username=username,
        num_pairs=num_pairs,
        num_samples=num_samples,
        coexistance_last_update_date=coexistance_last_update_date,
        coexistance_last_update_time=coexistance_last_update_time,
        autocluster_last_update_date=autocluster_last_update_date,
        autocluster_last_update_time=autocluster_last_update_time,
        lexical_last_update_date=lexical_last_update_date,
        lexical_last_update_time=lexical_last_update_time,
        values_last_update_date=values_last_update_date,
        values_last_update_time=values_last_update_time,
        lexical_num_processed=lexical_num_processed,
        autocluster_num_processed=autocluster_num_processed,
        values_num_processed=values_num_processed,
        coexistance_num_processed=coexistance_num_processed

        )

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        organisation = request.form['organisation']

        if len(username) < 1:
            flash('Your username must be at least one character.')
        elif len(password) < 5:
            flash('Your password must be at least 5 characters.')
        elif not User(username).register(password, email, organisation):
            flash('A user with that username already exists.')
        else:
            session['username'] = username
            return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not User(username).verify_password(password):
            flash('Invalid login.')
        else:
            session['username'] = username
            flash('Logged in.')
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out.')
    return redirect(url_for('index'))

@app.route('/attribute_curation/<username>', methods=['GET', 'POST'])
def attribute_curator_home(username):
    logged_in_username = session.get('username')
    # user_being_viewed_username = username
    # user_being_viewed = User(user_being_viewed_username)


    if logged_in_username:

        username_tag = session.get('username')
        settings = current_settings(username_tag)
        sort_type = settings[0]
        vioscreen_stop = settings[1]
        
        profile_info = profile_stats(logged_in_username)
        all_pairs_curated = profile_info[0]
        SUGGESTED_MERGE_decisions = profile_info[1]
        SUGGESTED_NOMERGE_decisions = profile_info[2]
        SUGGESTED_REVERSEMERGE_decisions = profile_info[3]
        TOTAL_MERGE = SUGGESTED_MERGE_decisions + SUGGESTED_REVERSEMERGE_decisions

        node_info = fetch_initial_pair_nodes(sort_type, vioscreen_stop)
        pair_id = node_info[1]

        if request.method == 'POST':
            form_dict = request.form.to_dict()
            print(form_dict , file=sys.stdout)

            if 'wipeData' in form_dict:
                user_data_wipe(username_tag)
                return redirect(url_for('attribute_curator_home', username=username_tag))

            elif form_dict.get('initial') == 'Continue Curating':

                if 'sort' in form_dict:
                    input_sort_type = form_dict.get('sort')
                    print('input_sort_type is: ' + str(input_sort_type), file=sys.stdout)
                    print('input_sort_type is: ' + str(input_sort_type), file=sys.stdout)
                    if input_sort_type != sort_type: # to change user setting in Neo4J
                        change_sort_type(username, input_sort_type)
                        print('changed sort_type from ' + str(sort_type) + ' to ' + str(input_sort_type), file=sys.stdout)

                if 'vioscreen_stop' in form_dict:
                    input_vioscreen_stop = form_dict.get('vioscreen_stop')
                    if input_vioscreen_stop != vioscreen_stop:
                        change_vioscreen_stop(username, input_vioscreen_stop)
                
                return redirect(url_for('attribute_curation_pair', pair_id=pair_id, username=username_tag))

                
            elif form_dict.get('initial') == 'Begin Curating':
                return redirect(url_for('attribute_curation_pair', pair_id=pair_id, username=username_tag))


        return render_template('attribute_curation_home.html',
        username=username,
        pair_id=pair_id,
        all_pairs_curated=all_pairs_curated,
        SUGGESTED_MERGE_decisions=SUGGESTED_MERGE_decisions,
        SUGGESTED_NOMERGE_decisions=SUGGESTED_NOMERGE_decisions,
        SUGGESTED_REVERSEMERGE_decisions=SUGGESTED_REVERSEMERGE_decisions,
        TOTAL_MERGE=TOTAL_MERGE,
        sort_type=sort_type,
        vioscreen_stop=vioscreen_stop
        ) 
    else:
        return redirect(url_for('login'))

@app.route('/attribute_curation/<username>/<int:pair_id>', methods=['GET','POST'])
def attribute_curation_pair(pair_id, username):
# def attribute_curation_pair(pair_id, username):

    logged_in_username = session.get('username')
    settings = current_settings(logged_in_username)
    sort_type = settings[0]
    vioscreen_stop = settings[1]

    results = get_next_pair_record(pair_id, sort_type, vioscreen_stop)

    if results == 'Node not in database':
        abort(404)

    else:
        if logged_in_username:
            current_pair_id = results[0]
            next_pair_id = results[1]
            current_pair_info = get_all_record_info(pair_id)
            pair_name = current_pair_info.get('name')
            good_attribute = current_pair_info.get('good_attribute')
            bad_attribute = current_pair_info.get('bad_attribute')
            levenshtein = current_pair_info.get('levenshtein')
            bad_facet_freq = current_pair_info.get('bad_facet_freq')
            good_facet_freq = current_pair_info.get('good_facet_freq')


            jaccard_coefficient = current_pair_info.get('jaccard_coefficient')
            degree1 = current_pair_info.get('degree1')
            degree2 = current_pair_info.get('degree2')
            break_no = current_pair_info.get('break_no')
            edge_total = current_pair_info.get('edge_total')
            edge_weight = current_pair_info.get('edge_weight')

            # values.py stuff

            type_match = current_pair_info.get('type_match')
            jaro_score = current_pair_info.get('jaro_score')
            top_value1 = current_pair_info.get('top_value1')
            top_value2 = current_pair_info.get('top_value2')
            exact_score = current_pair_info.get('exact_score')


            lexical_info = get_lexical_info(pair_id)
            lexical_issues = lexical_info[0]
            bad_words = lexical_info[1]
            possible_camelCase = lexical_info[2]

            # previous decision? get relationship type

            last_decision = get_last_decision(username, pair_id)

            print('current id: ' + str(current_pair_id), file=sys.stdout)
            print('next id: ' + str(next_pair_id), file=sys.stdout)

            if request.method == 'POST':

                form_dict = request.form.to_dict()
                print(form_dict , file=sys.stdout)


                if 'merge' in request.form:
                    make_relationship(username, pair_id, "SUGGESTED_MERGE", next_pair_id)
                    return redirect(url_for('attribute_curation_pair', pair_id=next_pair_id, username=username, sort_type=sort_type))

                if 'no_merge' in request.form:
                    make_relationship(username, pair_id, "SUGGESTED_NOMERGE", next_pair_id)
                    return redirect(url_for('attribute_curation_pair', pair_id=next_pair_id, username=username, sort_type=sort_type))

                if 'reverse_merge' in request.form:
                    make_relationship(username, pair_id, "SUGGESTED_REVERSEMERGE", next_pair_id)
                    return redirect(url_for('attribute_curation_pair', pair_id=next_pair_id, username=username, sort_type=sort_type))

                if 'skip' in request.form:
                    make_relationship(username, pair_id, "SKIPPED", next_pair_id)
                    return redirect(url_for('attribute_curation_pair', pair_id=next_pair_id, username=username, sort_type=sort_type))



            return render_template('attribute_curation_pair.html',
                username=username,
                pair_name=pair_name,
                pair_id=current_pair_id,
                next_pair_id=next_pair_id,
                good_attribute=good_attribute,
                bad_attribute=bad_attribute,
                levenshtein=levenshtein,
                bad_facet_freq=bad_facet_freq,
                good_facet_freq=good_facet_freq,

                jaccard_coefficient=jaccard_coefficient,
                degree1=degree1,
                degree2=degree2,
                break_no=break_no,
                edge_total=edge_total,
                edge_weight=edge_weight,

                type_match=type_match,
                jaro_score=jaro_score,
                top_value1=top_value1,
                top_value2=top_value2,
                exact_score=exact_score,

                lexical_issues=lexical_issues,
                bad_words=bad_words,
                possible_camelCase=possible_camelCase,

                last_decision=last_decision,
                sort_type=sort_type,
                vioscreen_stop=vioscreen_stop

                )


        else:
            return redirect(url_for('login'))



# @app.route('/attribute_curation/<int:pair_id>', methods=['POST'])
# def attribute_curation_pair(pair_id):

#     logged_in_username = session.get('username')
#     if logged_in_username:


#     else:
#         return redirect(url_for('login'))

@app.route('/documentation', methods=['GET'])
def documentation():
    logged_in_username = session.get('username')

    if logged_in_username:
        return render_template('documentation.html')
    else:
        return redirect(url_for('login'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/test', methods=['GET', 'POST'])
def page_test():
    return 'This direct passed test'

