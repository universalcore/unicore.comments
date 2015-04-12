"""stream settings table

Revision ID: 2a7430252168
Revises: 1c8ee76214e4
Create Date: 2015-04-12 16:36:40.609723

"""

# revision identifiers, used by Alembic.
revision = '2a7430252168'
down_revision = '1c8ee76214e4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('stream_settings',
    sa.Column('app_uuid', sqlalchemy_utils.types.uuid.UUIDType(binary=False), nullable=False),
    sa.Column('content_uuid', sqlalchemy_utils.types.uuid.UUIDType(binary=False), nullable=False),
    sa.Column('settings', sqlalchemy_utils.types.json.JSONType(), nullable=True),
    sa.PrimaryKeyConstraint('app_uuid', 'content_uuid')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('stream_settings')
    ### end Alembic commands ###
