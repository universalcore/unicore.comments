"""banned_users table

Revision ID: 226021631619
Revises: 2dff97787d0d
Create Date: 2015-04-10 09:12:28.060956

"""

# revision identifiers, used by Alembic.
revision = '226021631619'
down_revision = '2dff97787d0d'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('banned_users',
    sa.Column('user_uuid', sqlalchemy_utils.types.uuid.UUIDType(binary=False), nullable=False),
    sa.Column('app_id', sqlalchemy_utils.types.uuid.UUIDType(binary=False), nullable=True),
    sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text(u'now()'), nullable=True),
    sa.PrimaryKeyConstraint('user_uuid', 'app_id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('banned_users')
    ### end Alembic commands ###